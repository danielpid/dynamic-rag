FROM public.ecr.aws/lambda/python:3.12

# install your heavy libraries
COPY requirements.txt .
RUN pip install -r requirements.txt

# Download the required packages (stopwords and punkt are used by LlamaIndex)
ENV NLTK_DATA=/usr/local/lib/python3.12/site-packages/nltk_data
RUN mkdir -p ${NLTK_DATA}
RUN python -c "import nltk; nltk.download('punkt', download_dir='${NLTK_DATA}')"
RUN python -c "import nltk; nltk.download('stopwords', download_dir='${NLTK_DATA}')"

# copy your function
COPY addDocumentToIndex.py .

# set handler: file.function
CMD ["addDocumentToIndex.handler"]
