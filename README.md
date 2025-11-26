# Dynamic RAG with LlamaIndex, PGVector, and AWS

This project is a demonstration of how to build a serverless, Retrieval-Augmented Generation (RAG) pipeline on AWS. It uses LlamaIndex, PGVector, and a React-based chat interface to allow users to ask questions about a static document.

## Architecture

The architecture is composed of two main parts:

1.  **Ingestion**: An API endpoint to ingest documents into the RAG pipeline. Documents are read from an S3 bucket, processed by a Lambda function to generate embeddings with LlamaIndex and OpenAI, and stored in a PGVector database.
2.  **Querying**: An API endpoint that takes a user's question, retrieves relevant context from the PGVector database, and uses an LLM to generate an answer.

The entire infrastructure is deployed on AWS using the AWS CDK.

## Technologies Used

- **Backend**: Python, AWS CDK, AWS Lambda, API Gateway, S3, RDS for PostgreSQL.
- **RAG**: LlamaIndex, PGVector, OpenAI.
- **Frontend**: React, TypeScript, Vite, TailwindCSS.

## Getting Started

### Prerequisites

- An AWS Account and configured credentials.
- Node.js and `pnpm`.
- Python 3.12.
- AWS CDK Toolkit.

### Backend Setup

1.  **Create a virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Deploy the CDK stack:**
    Before deploying, make sure your AWS credentials are set up correctly. Then run:
    ```bash
    cdk deploy --all --require-approval never
    ```
    This will provision all the necessary AWS resources. After the deployment is complete, take note of the API Gateway URL from the output.

### Frontend Setup

1.  **Navigate to the UI directory:**

    ```bash
    cd src/ui
    ```

2.  **Install dependencies:**

    ```bash
    pnpm install
    ```

3.  **Configure the API URL:**
    Create a `.env.local` file in the `src/ui` directory and add the API Gateway URL:

    ```
    VITE_API_URL=YOUR_API_GATEWAY_URL
    ```

    Replace `YOUR_API_GATEWAY_URL` with the URL you got from the CDK deployment output.

4.  **Run the development server:**
    ```bash
    pnpm dev
    ```
    The application will be available at `http://localhost:5173`.

## Deployment

The project is deployed using the AWS CDK. The `cdk deploy --all --require-approval never` command will deploy both the backend and frontend stacks.

Any changes to the infrastructure or code can be deployed by running the same command again.
