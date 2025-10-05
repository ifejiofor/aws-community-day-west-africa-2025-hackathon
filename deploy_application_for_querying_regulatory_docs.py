import boto3
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

class AmazonQBusiness:
    """Class that uses Amazon Q Business to deploy an application for querying regulatory docs"""

    def __init__(self, config_file: str = 'config.json'):
        """Initialize with configuration from file"""
        self.config = self.load_config(config_file)
        self.qbusiness = boto3.client('qbusiness', region_name=self.config['aws']['region'])
    
    def deploy(self) -> Dict[str, str]:
        """Deploy the complete Q Business setup"""
        print("Starting Amazon Q Business deployment...")
        print("=" * 50)
        
        # Validate configuration
        if not self.validate_config():
            raise ValueError("Configuration validation failed. Please fix the errors and try again.")
        
        try:
            # Create application
            application_id = self.create_application()
            
            # Create index
            index_id = self.create_index(application_id)
            
            # Create data source
            data_source_id = self.create_data_source(application_id, index_id)
            
            # Start initial sync
            execution_id = self.start_data_source_sync(application_id, index_id, data_source_id)
            
            resources = {
                'applicationId': application_id,
                'indexId': index_id,
                'dataSourceId': data_source_id,
                'executionId': execution_id
            }
            
            print("\n" + "=" * 50)
            print("Deployment completed successfully!")
            print("Resources created:")
            for key, value in resources.items():
                print(f"  {key}: {value}")
            
            return resources
            
        except Exception as e:
            print(f"Deployment failed: {str(e)}")
            raise
    
    def create_application(self) -> str:
        """Create Amazon Q Business application"""
        print("Creating Amazon Q Business application...")
        
        app_config = self.config['application']
        
        params = {
            'displayName': app_config['displayName'],
            'description': app_config['description'],
            'identityType': app_config['identityType'],
            'iamIdentityProviderArn': app_config['iamIdentityProviderArn'],
            'clientIdsForOIDC': [],  # Empty for IAM Identity Center
            'qAppsConfiguration': app_config['qAppsConfiguration'],
            'personalizationConfiguration': app_config['personalizationConfiguration'],
            'attachmentsConfiguration': app_config['attachmentsConfiguration']
        }
        
        application = self.qbusiness.create_application(**params)
        application_id = application['applicationId']
        
        print(f"Application created with ID: {application_id}")
        return application_id

    def create_index(self, application_id: str) -> str:
        """Create index for the application"""
        print("Creating index...")
        
        index_config = self.config['index']
        
        params = {
            'applicationId': application_id,
            'displayName': index_config['displayName'],
            'description': index_config['description'],
            'type': index_config['type'],
            'capacityConfiguration': index_config['capacityConfiguration'],
            'documentAttributeConfigurations': index_config['documentAttributeConfigurations']
        }
        
        index = self.qbusiness.create_index(**params)
        index_id = index['indexId']
        
        print(f"Index created with ID: {index_id}")
        return index_id

    def create_data_source(self, application_id: str, index_id: str) -> str:
        """Create S3 data source"""
        print("Creating S3 data source...")
        
        ds_config = self.config['dataSource']
        
        params = {
            'applicationId': application_id,
            'indexId': index_id,
            'displayName': ds_config['displayName'],
            'description': ds_config['description'],
            'configuration': ds_config['configuration'],
            'syncSchedule': ds_config['syncSchedule'],
            'roleArn': ds_config['roleArn']
        }
        
        data_source = self.qbusiness.create_data_source(**params)
        data_source_id = data_source['dataSourceId']
        
        print(f"Data source created with ID: {data_source_id}")
        return data_source_id

    def start_data_source_sync(self, application_id: str, index_id: str, data_source_id: str) -> str:
        """Start initial sync of the data source"""
        print("Starting data source synchronization...")
        
        sync_response = self.qbusiness.start_data_source_sync_job(
            applicationId=application_id,
            indexId=index_id,
            dataSourceId=data_source_id
        )
        
        execution_id = sync_response['executionId']
        print(f"Sync job started with execution ID: {execution_id}")
        return execution_id
    
    def load_config(self, config_file: str) -> Dict[Any, Any]:
        """Load configuration from JSON file"""
        try:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Configuration file '{config_file}' not found")
                
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Validate required configuration sections
            required_sections = ['aws', 'application', 'index', 'dataSource']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required configuration section: {section}")
                    
            print(f"Configuration loaded successfully from {config_file}")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise Exception(f"Error loading configuration: {e}")

    def validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Check for placeholder values that need to be replaced
        if "<YOUR-ACCOUNT>" in self.config['dataSource']['roleArn']:
            errors.append("Please replace '<YOUR-ACCOUNT>' in dataSource.roleArn with your actual AWS account ID")
            
        if self.config['dataSource']['configuration']['additionalProperties']['bucketName'] == "<YOUR-S3-BUCKET-NAME>":
            errors.append("Please replace '<YOUR-S3-BUCKET-NAME>' in dataSource.configuration.additionalProperties.bucketName with your actual S3 bucket name")
        
        if self.config['application']['iamIdentityProviderArn'] == "<YOUR-IAM-IDENTITY-CENTER-ARN>":
            errors.append("Please replace '<YOUR-IAM-IDENTITY-CENTER-ARN>' in application.iamIdentityProviderArn with your actual IAM Identity Center ARN")
            
        # Validate ARN format
        iam_arn = self.config['application']['iamIdentityProviderArn']
        if not iam_arn.startswith('arn:aws:sso:::instance/'):
            errors.append("Invalid iamIdentityProviderArn format")
            
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
            
        print("Configuration validation passed")
        return True

def main():
    """Main execution function"""
    config_file = 'config.json'
    
    try:
        # Initialize deployment
        deployment = AmazonQBusiness(config_file)
        
        # Deploy resources
        resources = deployment.deploy()
        
        # Save resource IDs to file for future reference
        output_file = 'deployment_output.json'
        with open(output_file, 'w') as f:
            json.dump(resources, f, indent=2)
        print(f"\nResource IDs saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
