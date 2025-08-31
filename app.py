import streamlit as st
import boto3
import os
import re
from botocore.exceptions import ClientError
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="S3 Cloud Manager",
    page_icon="☁️",
    layout="wide"
)

# Initialize session state variables
if 's3_connected' not in st.session_state:
    st.session_state.s3_connected = False
if 'buckets' not in st.session_state:
    st.session_state.buckets = []
if 'current_bucket' not in st.session_state:
    st.session_state.current_bucket = None
if 'bucket_files' not in st.session_state:
    st.session_state.bucket_files = []
if 's3_resource' not in st.session_state:
    st.session_state.s3_resource = None
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False
if 'file_to_delete' not in st.session_state:
    st.session_state.file_to_delete = None
if 'endpoint_url' not in st.session_state:
    st.session_state.endpoint_url = ""
if 'region_name' not in st.session_state:
    st.session_state.region_name = ""

# Validate bucket name according to S3 rules
def validate_bucket_name(name):
    """
    Validate bucket name according to S3 naming rules:
    - Must be between 3 and 63 characters long
    - Must consist only of lowercase letters, numbers, dots (.), and hyphens (-)
    - Must start and end with a letter or number
    - Must not contain two adjacent periods
    - Must not be formatted as an IP address (e.g., 192.168.1.1)
    - Must not start with 'xn--'
    """
    if len(name) < 3 or len(name) > 63:
        return False, "Bucket name must be between 3 and 63 characters"

    if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', name):
        return False, "Bucket name can only contain lowercase letters, numbers, dots, and hyphens, and must start and end with a letter or number"

    if '..' in name:
        return False, "Bucket name cannot contain two adjacent periods"

    if re.match(r'^\d+\.\d+\.\d+\.\d+$', name):
        return False, "Bucket name cannot be formatted as an IP address"

    if name.startswith('xn--'):
        return False, "Bucket name cannot start with 'xn--'"

    return True, "Valid bucket name"

# Function to list files in bucket
def list_bucket_files(bucket_name):
    try:
        bucket_obj = st.session_state.s3_resource.Bucket(bucket_name)
        files = list(bucket_obj.objects.all())
        return [obj.key for obj in files]
    except Exception as e:
        st.error(f"Error listing files: {e}")
        return []

# Function to delete file from bucket
def delete_file_from_bucket(bucket_name, file_name):
    try:
        st.session_state.s3_resource.Object(bucket_name, file_name).delete()
        return True, f"File '{file_name}' deleted successfully!"
    except Exception as e:
        return False, f"Error deleting file: {e}"

# App title and description
st.title("☁️ S3 Cloud Manager")
st.markdown("""
Manage your S3 storage: connect to your cloud provider, create buckets, and upload/download files.
""")

# Sidebar for connection details
with st.sidebar:
    st.header("Connection Settings")

    # Provider selection
    provider = st.radio(
        "Select Cloud Provider",
        ["AWS", "ArvanCloud", "Custom"],
        index=0,
        help="Select your S3 compatible cloud provider"
    )

    # Pre-fill values based on provider selection
    if provider == "AWS":
        default_endpoint = "https://s3.amazonaws.com"
        default_region = "us-east-1"
    elif provider == "ArvanCloud":
        default_endpoint = "https://s3.ir-thr-at1.arvanstorage.ir"
        default_region = "ir-thr-at1"
    else:  # Custom
        default_endpoint = ""
        default_region = ""

    # Input fields for connection details
    endpoint_url = st.text_input(
        "Endpoint URL",
        value=default_endpoint,
        placeholder="https://s3.amazonaws.com",
        help="S3 compatible endpoint URL"
    )

    region_name = st.text_input(
        "Region Name",
        value=default_region,
        placeholder="us-east-1",
        help="Region name for your S3 service"
    )

    # Input fields for credentials
    access_key = st.text_input("Access Key ID", type="password", key="access_key")
    secret_key = st.text_input("Secret Access Key", type="password", key="secret_key")

    # Connect button
    if st.button("Connect to S3 Service"):
        if not access_key or not secret_key:
            st.error("Please provide both Access Key and Secret Key")
        elif not endpoint_url:
            st.error("Please provide Endpoint URL")
        elif not region_name:
            st.error("Please provide Region Name")
        else:
            try:
                with st.spinner("Connecting to S3 service..."):
                    # Initialize S3 resource
                    s3_resource = boto3.resource(
                        's3',
                        endpoint_url=endpoint_url,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region_name
                    )

                    # Test connection by listing buckets
                    buckets = list(s3_resource.buckets.all())
                    st.session_state.buckets = [bucket.name for bucket in buckets]
                    st.session_state.s3_resource = s3_resource
                    st.session_state.s3_connected = True
                    st.session_state.endpoint_url = endpoint_url
                    st.session_state.region_name = region_name
                    st.session_state.provider = provider

                    st.success("Connected successfully!")

            except Exception as e:
                st.error(f"Connection failed: {str(e)}")

    # Disconnect button
    if st.session_state.s3_connected:
        if st.button("Disconnect"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.s3_connected = False
            st.session_state.buckets = []
            st.session_state.current_bucket = None
            st.session_state.bucket_files = []
            st.session_state.confirm_delete = False
            st.session_state.file_to_delete = None
            st.rerun()

# Main app functionality
if st.session_state.s3_connected and st.session_state.s3_resource:
    # Display connection status
    st.success(f"✅ Connected to {st.session_state.provider} S3")
    st.info(f"**Endpoint:** {st.session_state.endpoint_url} | **Region:** {st.session_state.region_name}")

    # Create two columns for bucket operations
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Bucket Operations")

        # Create new bucket
        st.markdown("#### Create New Bucket")
        new_bucket_name = st.text_input("Bucket Name", placeholder="my-bucket-name", key="new_bucket")

        # Show bucket naming rules as a tooltip/info
        st.markdown("""
        **Bucket Naming Rules:**
        - 3-63 characters, lowercase letters, numbers, dots, hyphens only
        - Must start and end with letter/number
        - No adjacent periods, IP addresses, or 'xn--' prefix
        - Examples: `my-bucket`, `data.storage123`
        """)

        if st.button("Create Bucket", key="create_bucket_btn"):
            if new_bucket_name:
                # Validate bucket name
                is_valid, message = validate_bucket_name(new_bucket_name)

                if not is_valid:
                    st.error(f"Invalid bucket name: {message}")
                else:
                    try:
                        with st.spinner("Creating bucket..."):
                            # Handle different regions (us-east-1 doesn't need LocationConstraint in AWS)
                            if st.session_state.provider == "AWS" and st.session_state.region_name == "us-east-1":
                                st.session_state.s3_resource.Bucket(new_bucket_name).create()
                            else:
                                st.session_state.s3_resource.Bucket(new_bucket_name).create(
                                    CreateBucketConfiguration={
                                        'LocationConstraint': st.session_state.region_name
                                    }
                                )
                            st.success(f"Bucket '{new_bucket_name}' created successfully!")
                            # Refresh bucket list
                            time.sleep(1)
                            buckets = list(st.session_state.s3_resource.buckets.all())
                            st.session_state.buckets = [bucket.name for bucket in buckets]
                    except ClientError as e:
                        error_code = e.response['Error']['Code']
                        if error_code == 'BucketAlreadyExists':
                            st.error("Bucket name is already taken. Please choose a different name.")
                        elif error_code == 'InvalidBucketName':
                            st.error("Invalid bucket name. Please follow the naming rules.")
                        else:
                            st.error(f"Error creating bucket: {e}")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")
            else:
                st.error("Please enter a bucket name")

        # Select existing bucket
        if st.session_state.buckets:
            st.subheader("Existing Buckets")
            selected_bucket = st.selectbox(
                "Select a bucket",
                st.session_state.buckets,
                index=0,
                key="bucket_selector"
            )

            if st.button("Use Selected Bucket", key="use_bucket_btn"):
                st.session_state.current_bucket = selected_bucket
                # List files in the bucket
                try:
                    with st.spinner("Loading bucket contents..."):
                        st.session_state.bucket_files = list_bucket_files(selected_bucket)
                    st.success(f"Now accessing bucket: {selected_bucket}")
                except ClientError as e:
                    st.error(f"Error accessing bucket: {e}")
        else:
            st.info("No buckets found. Create a new bucket to get started.")

    with col2:
        st.subheader("Current Bucket")

        if st.session_state.current_bucket:
            st.info(f"Selected Bucket: **{st.session_state.current_bucket}**")

            # File operations
            st.subheader("File Operations")

            # Upload file
            st.markdown("#### Upload File")
            uploaded_file = st.file_uploader("Choose a file to upload", key="uploader")
            if uploaded_file is not None:
                if st.button("Upload to Bucket", key="upload_btn"):
                    try:
                        with st.spinner("Uploading file..."):
                            bucket_obj = st.session_state.s3_resource.Bucket(st.session_state.current_bucket)
                            # Upload the file
                            bucket_obj.upload_fileobj(
                                uploaded_file,
                                uploaded_file.name,
                                ExtraArgs={'ACL': 'private'}
                            )
                            st.success(f"File '{uploaded_file.name}' uploaded successfully!")
                            # Refresh file list
                            st.session_state.bucket_files = list_bucket_files(st.session_state.current_bucket)
                    except Exception as e:
                        st.error(f"Error uploading file: {e}")

            # Download file
            st.markdown("#### Download File")
            if st.session_state.bucket_files:
                file_to_download = st.selectbox("Select file to download", st.session_state.bucket_files, key="download_select")

                # Get download path
                default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                download_dir = st.text_input("Download directory", value=default_download_dir, key="download_dir")
                download_filename = st.text_input("Save as filename", value=file_to_download, key="download_filename")
                download_path = os.path.join(download_dir, download_filename)

                if st.button("Download Selected File", key="download_btn"):
                    try:
                        with st.spinner("Downloading file..."):
                            bucket_obj = st.session_state.s3_resource.Bucket(st.session_state.current_bucket)

                            # Create directory if it doesn't exist
                            os.makedirs(download_dir, exist_ok=True)

                            # Download the file
                            bucket_obj.download_file(file_to_download, download_path)
                            st.success(f"File downloaded successfully to: {download_path}")

                    except Exception as e:
                        st.error(f"Error downloading file: {e}")
            else:
                st.info("No files in this bucket")

            # Delete file
            st.markdown("#### Delete File")
            if st.session_state.bucket_files:
                file_to_delete = st.selectbox("Select file to delete", st.session_state.bucket_files, key="delete_select")

                # Store the selected file for deletion
                if file_to_delete != st.session_state.get('file_to_delete'):
                    st.session_state.file_to_delete = file_to_delete
                    st.session_state.confirm_delete = False

                # Confirmation for deletion
                confirm_delete = st.checkbox("I understand this action cannot be undone",
                                           value=st.session_state.confirm_delete,
                                           key="confirm_delete_checkbox")

                # Update session state when checkbox changes
                if confirm_delete != st.session_state.confirm_delete:
                    st.session_state.confirm_delete = confirm_delete

                if st.button("Delete Selected File",
                            key="delete_btn",
                            disabled=not st.session_state.confirm_delete,
                            type="primary"):
                    try:
                        with st.spinner("Deleting file..."):
                            success, message = delete_file_from_bucket(st.session_state.current_bucket, file_to_delete)
                            if success:
                                st.success(message)
                                # Refresh file list
                                st.session_state.bucket_files = list_bucket_files(st.session_state.current_bucket)
                                st.session_state.confirm_delete = False
                                st.session_state.file_to_delete = None
                                st.rerun()
                            else:
                                st.error(message)
                    except Exception as e:
                        st.error(f"Error deleting file: {e}")
            else:
                st.info("No files in this bucket")

            # Display files in the bucket
            st.subheader("Files in Bucket")
            if st.session_state.bucket_files:
                st.write(f"Found {len(st.session_state.bucket_files)} file(s):")
                for file_name in st.session_state.bucket_files:
                    st.write(f"📄 {file_name}")

                # Refresh button
                if st.button("Refresh File List", key="refresh_btn"):
                    try:
                        with st.spinner("Refreshing file list..."):
                            st.session_state.bucket_files = list_bucket_files(st.session_state.current_bucket)
                        st.success("File list refreshed!")
                    except Exception as e:
                        st.error(f"Error refreshing file list: {e}")
            else:
                st.info("No files in this bucket")

        else:
            st.info("Please select a bucket from the options on the left")

else:
    # Show connection instructions
    st.info("Please enter your S3 service credentials in the sidebar to connect")

    # Instructions
    st.markdown("""
    ### How to get your S3 credentials

    **For AWS S3:**
    1. Log in to your [AWS Console](https://aws.amazon.com/console/)
    2. Go to **IAM** → **Users**
    3. Create a user with **AmazonS3FullAccess** policy
    4. Generate **Access Key** and **Secret Key**
    5. Use endpoint: `https://s3.amazonaws.com` and your region (e.g., `us-east-1`)

    **For ArvanCloud:**
    1. Log in to your [ArvanCloud account](https://panel.arvancloud.com)
    2. Go to **Cloud Storage** → **Object Storage**
    3. Create a new bucket or select an existing one
    4. Go to **Access Keys** section
    5. Generate **Access Key** and **Secret Key**
    6. Use endpoint: `https://s3.ir-thr-at1.arvanstorage.ir` and region: `ir-thr-at1`

    **For Other S3 Compatible Services:**
    1. Check your provider's documentation for endpoint URL and region
    2. Obtain Access Key and Secret Key from your provider's dashboard
    """)

    # Common endpoints examples
    with st.expander("Common S3 Endpoint Examples"):
        st.markdown("""
        - **AWS:** `https://s3.amazonaws.com` (region: us-east-1)
        - **AWS other regions:** `https://s3.eu-west-1.amazonaws.com` (region: eu-west-1)
        - **ArvanCloud:** `https://s3.ir-thr-at1.arvanstorage.ir` (region: ir-thr-at1)
        - **DigitalOcean Spaces:** `https://nyc3.digitaloceanspaces.com` (region: nyc3)
        - **Linode Object Storage:** `https://us-east-1.linodeobjects.com` (region: us-east-1)
        - **Wasabi:** `https://s3.wasabisys.com` (region: us-east-1)
        """)

# Footer
st.markdown("---")
st.markdown("### 💡 Tips & Information")
st.markdown("""
- **Bucket names** must be globally unique across all users of the same provider
- **Follow the bucket naming rules** to avoid errors
- Files uploaded to **private buckets** require authentication to access
- **File deletion is permanent** - deleted files cannot be recovered
- Different providers may have slightly different S3 API implementations
- For large files, upload/download might take some time
""")

# Warning about file deletion
if st.session_state.get('confirm_delete', False):
    st.warning("⚠️ File deletion is enabled. Deleted files cannot be recovered!")

# Add some custom CSS for better styling
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .stExpander {
        border: 1px solid #e6e6e6;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 1rem;
    }
    .warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .delete-button {
        background-color: #dc3545;
        color: white;
    }
    .delete-button:hover {
        background-color: #c82333;
        color: white;
    }
</style>
""", unsafe_allow_html=True)
