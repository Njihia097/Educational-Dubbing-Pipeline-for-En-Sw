import os
import io
import socket
from urllib.parse import urlparse, urlunparse
import boto3
from botocore.client import Config

class StorageAdapter:
    def __init__(self):
        self.backend = os.getenv("STORAGE_BACKEND", "minio")
        self.bucket = os.getenv("S3_BUCKET", "edu-dubbing")

        # Derive endpoint with a sensible local default
        endpoint = os.getenv("S3_ENDPOINT", "http://localhost:9000")

        # If configured to use the docker service name 'minio' but we're running
        # outside docker (common during local dev), transparently map to localhost.
        try:
            parsed = urlparse(endpoint)
            if parsed.hostname == "minio":
                try:
                    socket.gethostbyname("minio")  # will raise if not resolvable
                except Exception:
                    parsed = parsed._replace(netloc=f"localhost:{parsed.port or 9000}")
                    endpoint = urlunparse(parsed)
        except Exception:
            # If URL parsing fails for any reason, fall back to the original value
            pass

        use_ssl = str(os.getenv("S3_SECURE", "false")).lower() in ("1", "true", "yes")

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            use_ssl=use_ssl,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

        # Ensure bucket exists
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception as e:
            # MinIO requires LocationConstraint for non-us-east-1 regions
            region = os.getenv("S3_REGION", "us-east-1")
            create_bucket_params = {"Bucket": self.bucket}
            if region != "us-east-1":
                create_bucket_params["CreateBucketConfiguration"] = {"LocationConstraint": region}
            try:
                self.client.create_bucket(**create_bucket_params)
            except self.client.exceptions.BucketAlreadyOwnedByYou:
                pass
            except self.client.exceptions.BucketAlreadyExists:
                pass
            except Exception as ce:
                print(f"Bucket creation failed: {ce}")

    def put(self, key: str, data: bytes, content_type="application/octet-stream"):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return self.url_for(key)

    def get(self, key: str):
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def url_for(self, key: str, expires=3600):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

storage = StorageAdapter()
