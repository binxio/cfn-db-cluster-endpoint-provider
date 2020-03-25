include Makefile.mk

NAME=cfn-db-cluster-endpoint-provider
S3_BUCKET_PREFIX=binxio-public
AWS_REGION=eu-central-1
S3_BUCKET=$(S3_BUCKET_PREFIX)-$(AWS_REGION)
ALL_REGIONS=$(shell aws --region $(AWS_REGION) \
		ec2 describe-regions 		\
		--query 'join(`\n`, Regions[?RegionName != `$(AWS_REGION)`].RegionName)' \
		--output text)


help:
	@echo 'make                 - builds a zip file to target/.'
	@echo 'make release         - builds a zip file and deploys it to s3.'
	@echo 'make clean           - the workspace.'
	@echo 'make test            - execute the tests, requires a working AWS connection.'
	@echo 'make deploy-provider - deploys the provider.'
	@echo 'make delete-provider - deletes the provider.'
	@echo 'make demo            - deploys the provider and the demo cloudformation stack.'
	@echo 'make delete-demo     - deletes the demo cloudformation stack.'


deploy: target/$(NAME)-$(VERSION).zip
	aws s3 --region $(AWS_REGION) \
		cp --acl public-read \
		cloudformation/cfn-resource-provider.yaml \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).yaml
	aws s3 --region $(AWS_REGION) \
		cp --acl public-read \
		target/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip
	aws s3 --region $(AWS_REGION) \
		cp --acl public-read \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
		s3://$(S3_BUCKET)/lambdas/$(NAME)-latest.zip

deploy-all-regions: deploy
	@for REGION in $(ALL_REGIONS); do \
		echo "copying to region $$REGION.." ; \
		aws s3 --region $$REGION \
			cp  --acl public-read \
			s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip; \
		aws s3 --region $$REGION \
			cp  --acl public-read \
			s3://$(S3_BUCKET)/lambdas/$(NAME)-$(VERSION).zip \
			s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-latest.zip; \
	done

undeploy:
	@for REGION in $(ALL_REGIONS); do \
                echo "removing lamdba from region $$REGION.." ; \
                aws s3 --region $(AWS_REGION) \
                        rm  \
                        s3://$(S3_BUCKET_PREFIX)-$$REGION/lambdas/$(NAME)-$(VERSION).zip; \
        done


do-push: deploy

do-build: target/$(NAME)-$(VERSION).zip

target/$(NAME)-$(VERSION).zip: src/*/*.py requirements.txt
	mkdir -p target/content
	docker build --build-arg ZIPFILE=$(NAME)-$(VERSION).zip -t $(NAME)-lambda:$(VERSION) -f Dockerfile.lambda . && \
		ID=$$(docker create $(NAME)-lambda:$(VERSION) /bin/true) && \
		docker export $$ID | (cd target && tar -xvf - $(NAME)-$(VERSION).zip) && \
		docker rm -f $$ID && \
		chmod ugo+r target/$(NAME)-$(VERSION).zip

clean:
	find src -type f -name \*.pyc | xargs rm
	find tests -type f -name \*.pyc | xargs rm

Pipfile.lock: Pipfile requirements.txt test-requirements.txt
	pipenv install -r requirements.txt
	pipenv install -d -r test-requirements.txt

test: Pipfile.lock
	for n in ./cloudformation/*.yaml ; do aws cloudformation validate-template --template-body file://$$n ; done
	PYTHONPATH=$(PWD)/src pipenv run pytest ./tests/test*.py

fmt:
	find src -type f -name \*.py | xargs black 
	find tests -type f -name \*.py | xargs black 

deploy-provider: target/$(NAME)-$(VERSION).zip
	sed -i '' \
	    -e 's~lambdas/$(NAME)-.*\.zip~lambdas/$(NAME)-$(VERSION).zip~' \
	    cloudformation/cfn-resource-provider.yaml
	aws cloudformation deploy \
                --capabilities CAPABILITY_IAM \
                --stack-name $(NAME) \
                --template-file ./cloudformation/cfn-resource-provider.yaml

delete-provider:
	aws cloudformation delete-stack --stack-name $(NAME)
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)

deploy-pipeline:
	aws cloudformation deploy \
                --capabilities CAPABILITY_IAM \
                --stack-name $(NAME)-pipeline \
                --template-file ./cloudformation/cicd-pipeline.yaml \
                --parameter-overrides \
                        S3BucketPrefix=$(S3_BUCKET_PREFIX)

delete-pipeline: 
	aws cloudformation delete-stack --stack-name $(NAME)-pipeline
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-pipeline

demo: VPC_ID = $(shell aws ec2  --output text --query 'Vpcs[?IsDefault].VpcId' describe-vpcs)
demo: SUBNET_IDS = $(shell aws ec2 --output text \
						describe-subnets --query 'Subnets[*].SubnetId' \
										 --filter Name=vpc-id,Values=$(VPC_ID) \
												  Name=default-for-az,Values=true | tr '\t' ',')
demo: 
	aws cloudformation deploy --stack-name $(NAME)-demo \
		--template-file ./cloudformation/demo-stack.yaml \
		--capabilities CAPABILITY_NAMED_IAM \
		--parameter-overrides 	VPC=$(VPC_ID) Subnets=$(SUBNET_IDS)

delete-demo:
	aws cloudformation delete-stack --stack-name $(NAME)-demo
	aws cloudformation wait stack-delete-complete  --stack-name $(NAME)-demo

