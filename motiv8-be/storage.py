"""
Storage abstraction for local filesystem (dev) and S3 (production)
"""

import os
import logging
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Check if we're using S3 (production) or local storage (development)
USE_S3 = os.getenv("S3_BUCKET") is not None
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client if needed
s3_client = None
if USE_S3:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    logger.info(f"Using S3 storage: bucket={S3_BUCKET}, region={AWS_REGION}")
else:
    logger.info("Using local filesystem storage")


class Storage:
    """Storage abstraction for files"""

    def __init__(self, directory: str):
        """
        Initialize storage for a specific directory

        Args:
            directory: Directory name (e.g., 'uploads', 'embeddings', 'generated')
        """
        self.directory = directory
        self.local_path = Path(directory)

        # Create local directory if using local storage
        if not USE_S3:
            self.local_path.mkdir(exist_ok=True)

    def save(self, filename: str, data: bytes) -> str:
        """
        Save file to storage

        Args:
            filename: Name of the file
            data: File data as bytes

        Returns:
            str: Full path or S3 key of saved file
        """
        if USE_S3:
            # Save to S3
            s3_key = f"{self.directory}/{filename}"
            try:
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=data
                )
                logger.info(f"Saved to S3: s3://{S3_BUCKET}/{s3_key}")
                return s3_key
            except ClientError as e:
                logger.error(f"Error saving to S3: {e}")
                raise
        else:
            # Save to local filesystem
            file_path = self.local_path / filename
            with open(file_path, 'wb') as f:
                f.write(data)
            logger.info(f"Saved to local: {file_path}")
            return str(file_path)

    def save_from_file(self, filename: str, source_path: str) -> str:
        """
        Save file from a local path to storage

        Args:
            filename: Name to save the file as
            source_path: Path to source file

        Returns:
            str: Full path or S3 key of saved file
        """
        with open(source_path, 'rb') as f:
            data = f.read()
        return self.save(filename, data)

    def get(self, filename: str) -> bytes:
        """
        Get file from storage

        Args:
            filename: Name of the file

        Returns:
            bytes: File data
        """
        if USE_S3:
            # Get from S3
            s3_key = f"{self.directory}/{filename}"
            try:
                response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                return response['Body'].read()
            except ClientError as e:
                logger.error(f"Error getting from S3: {e}")
                raise
        else:
            # Get from local filesystem
            file_path = self.local_path / filename
            with open(file_path, 'rb') as f:
                return f.read()

    def get_path(self, filename: str) -> str:
        """
        Get the full path or S3 key for a file

        Args:
            filename: Name of the file

        Returns:
            str: Full local path or S3 key
        """
        if USE_S3:
            return f"{self.directory}/{filename}"
        else:
            return str(self.local_path / filename)

    def exists(self, filename: str) -> bool:
        """
        Check if file exists in storage

        Args:
            filename: Name of the file

        Returns:
            bool: True if file exists
        """
        if USE_S3:
            s3_key = f"{self.directory}/{filename}"
            try:
                s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
                return True
            except ClientError:
                return False
        else:
            return (self.local_path / filename).exists()

    def delete(self, filename: str) -> bool:
        """
        Delete file from storage

        Args:
            filename: Name of the file

        Returns:
            bool: True if successful
        """
        if USE_S3:
            s3_key = f"{self.directory}/{filename}"
            try:
                s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                logger.info(f"Deleted from S3: s3://{S3_BUCKET}/{s3_key}")
                return True
            except ClientError as e:
                logger.error(f"Error deleting from S3: {e}")
                return False
        else:
            file_path = self.local_path / filename
            if file_path.exists():
                os.remove(file_path)
                logger.info(f"Deleted from local: {file_path}")
                return True
            return False

    def download_to_local(self, filename: str, local_path: str) -> str:
        """
        Download file from storage to a local path (useful for processing)

        Args:
            filename: Name of the file in storage
            local_path: Local path to download to

        Returns:
            str: Local path where file was downloaded
        """
        if USE_S3:
            # Download from S3 to local path
            s3_key = f"{self.directory}/{filename}"
            try:
                s3_client.download_file(S3_BUCKET, s3_key, local_path)
                logger.info(f"Downloaded from S3 to local: {local_path}")
                return local_path
            except ClientError as e:
                logger.error(f"Error downloading from S3: {e}")
                raise
        else:
            # File is already local, just return the path
            return str(self.local_path / filename)


# Create storage instances for different directories
uploads_storage = Storage("uploads")
embeddings_storage = Storage("embeddings")
generated_storage = Storage("generated")
