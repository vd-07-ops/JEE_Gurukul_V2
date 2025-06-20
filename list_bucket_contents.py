from cloud_config import storage_client, BUCKET_NAME

def list_bucket_contents():
    """List all files in the bucket."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs()
    
    print(f"\nContents of bucket '{BUCKET_NAME}':")
    print("-" * 50)
    for blob in blobs:
        print(f"- {blob.name}")
    print("-" * 50)

if __name__ == "__main__":
    list_bucket_contents() 