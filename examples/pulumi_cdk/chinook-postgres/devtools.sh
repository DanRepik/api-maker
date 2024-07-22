alias up="pulumi up --yes"
alias down="pulumi destroy --yes"

alias select_local="export AWS_PROFILE=localstack; pulumi stack select local"
alias select_aws="export AWS_PROFILE=admin; pulumi stack select aws-dev"

# import playground commands
source "$(dirname "$0")/../../../dev_playground/devtools.sh"

export AWS_PROFILE=localstack
