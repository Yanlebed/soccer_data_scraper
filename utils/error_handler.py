"""
Error handling and notification utilities.
"""
import boto3
import json
import traceback
import logging
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sns_client = boto3.client('sns')
cloudwatch_client = boto3.client('cloudwatch')


class ErrorHandler:
    """Handles errors and sends notifications."""

    def __init__(self, function_name, sns_topic_arn=None):
        """
        Initialize the error handler.

        Args:
            function_name: Name of the Lambda function
            sns_topic_arn: ARN of the SNS topic for notifications
        """
        self.function_name = function_name
        self.sns_topic_arn = sns_topic_arn

    def handle_exception(self, exception, context=None, custom_message=None):
        """
        Handle an exception by logging it and sending notifications.

        Args:
            exception: The exception that occurred
            context: Lambda context object
            custom_message: Optional custom message to include

        Returns:
            Error response object
        """
        # Get full stack trace
        stack_trace = traceback.format_exc()

        # Create error message
        error_type = type(exception).__name__
        error_message = str(exception)
        timestamp = datetime.now().isoformat()

        # Create structured log entry
        log_entry = {
            'timestamp': timestamp,
            'function_name': self.function_name,
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace
        }

        if context:
            log_entry['request_id'] = context.aws_request_id
            log_entry['function_version'] = context.function_version
            log_entry['memory_limit'] = context.memory_limit_in_mb
            log_entry['remaining_time'] = context.get_remaining_time_in_millis()

        if custom_message:
            log_entry['custom_message'] = custom_message

        # Log the error
        logger.error(json.dumps(log_entry))

        # Publish metric to CloudWatch
        self._publish_metric(error_type)

        # Send SNS notification if configured
        if self.sns_topic_arn:
            self._send_notification(log_entry)

        # Return formatted error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_type,
                'message': error_message,
                'timestamp': timestamp
            })
        }

    def _publish_metric(self, error_type):
        """Publish error metric to CloudWatch."""
        try:
            cloudwatch_client.put_metric_data(
                Namespace='FootballScraper',
                MetricData=[
                    {
                        'MetricName': 'ErrorCount',
                        'Dimensions': [
                            {
                                'Name': 'FunctionName',
                                'Value': self.function_name
                            },
                            {
                                'Name': 'ErrorType',
                                'Value': error_type
                            }
                        ],
                        'Value': 1,
                        'Unit': 'Count'
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Failed to publish metric: {str(e)}")

    def _send_notification(self, log_entry):
        """Send error notification via SNS."""
        try:
            subject = f"Error in {self.function_name}"
            message = (
                f"Function: {self.function_name}\n"
                f"Error Type: {log_entry['error_type']}\n"
                f"Error Message: {log_entry['error_message']}\n"
                f"Timestamp: {log_entry['timestamp']}\n\n"
                f"Stack Trace:\n{log_entry['stack_trace']}"
            )

            if 'custom_message' in log_entry:
                message = f"Custom Message: {log_entry['custom_message']}\n\n" + message

            sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=message
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")