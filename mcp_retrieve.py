import boto3 
import logging
import sys
import os
import json

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("retrieve")

script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "knowledgebase.json")
    
def load_config():    
    config = None

    try:    
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)    
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        # boto3로 region 조회
        config = {}
        session = boto3.Session()
        region = session.region_name
        config['region'] = region
        config['knowledge_base_id'] = ''

    return config

config = load_config()

bedrock_region = config.get('region', 'us-west-2')
knowledge_base_id = config.get('knowledge_base_id', '')
number_of_results = 5

aws_access_key = config.get('aws', {}).get('access_key_id')
aws_secret_key = config.get('aws', {}).get('secret_access_key')
aws_session_token = config.get('aws', {}).get('session_token')

if aws_access_key and aws_secret_key:
    bedrock_agent_runtime_client = boto3.client(
        "bedrock-agent-runtime", 
        region_name=bedrock_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
    )
else:
    bedrock_agent_runtime_client = boto3.client(
        "bedrock-agent-runtime", region_name=bedrock_region)

def retrieve(query):
    response = bedrock_agent_runtime_client.retrieve(
        retrievalQuery={"text": query},
        knowledgeBaseId=knowledge_base_id,
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": number_of_results},
            },
        )
    
    # logger.info(f"response: {response}")
    retrieval_results = response.get("retrievalResults", [])
    # logger.info(f"retrieval_results: {retrieval_results}")

    json_docs = []
    for result in retrieval_results:
        text = url = name = None
        if "content" in result:
            content = result["content"]
            if "text" in content:
                text = content["text"]

        if "location" in result:
            location = result["location"]
            if "s3Location" in location:
                uri = location["s3Location"]["uri"] if location["s3Location"]["uri"] is not None else ""
                
                name = uri.split("/")[-1]
                # encoded_name = parse.quote(name)                
                # url = f"{path}/{doc_prefix}{encoded_name}"
                url = uri # TODO: add path and doc_prefix
                
            elif "webLocation" in location:
                url = location["webLocation"]["url"] if location["webLocation"]["url"] is not None else ""
                name = "WEB"

        json_docs.append({
            "contents": text,              
            "reference": {
                "url": url,                   
                "title": name,
                "from": "RAG"
            }
        })
    logger.info(f"json_docs: {json_docs}")

    return json.dumps(json_docs, ensure_ascii=False)