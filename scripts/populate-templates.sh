#!/bin/bash

# Script to populate DynamoDB Templates table with notification templates

set -e

AWS_REGION="ap-south-1"

echo "Populating Templates table with notification templates..."

# Welcome/Registration Template
aws dynamodb put-item \
    --table-name Templates \
    --region $AWS_REGION \
    --item '{
        "TemplateType": {"S": "Registration"},
        "Channel": {"S": "email"},
        "TemplateId": {"S": "REG_EMAIL_001"},
        "Subject": {"S": "Welcome to MLera - {Name}!"},
        "Body": {"S": "Hi {Name},\n\nWelcome to MLera! We are excited to have you on board.\n\nYou can now access all our courses and start your learning journey.\n\nBest regards,\nMLera Team"},
        "Version": {"N": "1"},
        "CreatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}
    }'

echo "✓ Registration template added"

# Module Completion Template
aws dynamodb put-item \
    --table-name Templates \
    --region $AWS_REGION \
    --item '{
        "TemplateType": {"S": "ModuleCompletion"},
        "Channel": {"S": "email"},
        "TemplateId": {"S": "MOD_COMP_EMAIL_001"},
        "Subject": {"S": "Congratulations {Name}! Module Completed"},
        "Body": {"S": "Hi {Name},\n\nCongratulations on completing the {ModuleName} module!\n\nYour Quiz Score: {QuizPercentage}%\n\nKeep up the great work and continue learning.\n\nBest regards,\nMLera Team"},
        "Version": {"N": "1"},
        "CreatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}
    }'

echo "✓ ModuleCompletion template added"

# Course Purchase Template
aws dynamodb put-item \
    --table-name Templates \
    --region $AWS_REGION \
    --item '{
        "TemplateType": {"S": "CoursePurchase"},
        "Channel": {"S": "email"},
        "TemplateId": {"S": "COURSE_PURCH_EMAIL_001"},
        "Subject": {"S": "Course Purchase Confirmed - {Name}"},
        "Body": {"S": "Hi {Name},\n\nThank you for purchasing the {CourseName} course!\n\nYou now have full access to all course materials and modules.\n\nStart learning today!\n\nBest regards,\nMLera Team"},
        "Version": {"N": "1"},
        "CreatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}
    }'

echo "✓ CoursePurchase template added"

# Account Deletion Template
aws dynamodb put-item \
    --table-name Templates \
    --region $AWS_REGION \
    --item '{
        "TemplateType": {"S": "AccountDeletion"},
        "Channel": {"S": "email"},
        "TemplateId": {"S": "ACC_DEL_EMAIL_001"},
        "Subject": {"S": "Account Deletion Confirmation - {Name}"},
        "Body": {"S": "Hi {Name},\n\nYour account has been successfully deleted from MLera.\n\nAll your data including course progress, quiz scores, and personal information has been permanently removed.\n\nIf this was a mistake or you wish to rejoin, you can create a new account anytime.\n\nThank you for being part of MLera.\n\nBest regards,\nMLera Team"},
        "Version": {"N": "1"},
        "CreatedAt": {"S": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"}
    }'

echo "✓ AccountDeletion template added"

echo ""
echo "=========================================="
echo "Templates Populated Successfully!"
echo "=========================================="
echo ""
echo "Templates added:"
echo "1. Registration (email) - TemplateId: REG_EMAIL_001"
echo "2. ModuleCompletion (email) - TemplateId: MOD_COMP_EMAIL_001"
echo "3. CoursePurchase (email) - TemplateId: COURSE_PURCH_EMAIL_001"
echo "4. AccountDeletion (email) - TemplateId: ACC_DEL_EMAIL_001"
echo ""
echo "Template variables:"
echo "- {Name}: User's name"
echo "- {Email}: User's email"
echo "- {QuizPercentage}: Quiz score (ModuleCompletion only)"
echo "- {ModuleName}: Module name (ModuleCompletion only)"
echo "- {CourseName}: Course name (CoursePurchase only)"
echo ""
echo "All templates are Version 1 with CreatedAt timestamp"
echo ""
