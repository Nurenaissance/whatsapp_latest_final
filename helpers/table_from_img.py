from django.http import JsonResponse
import boto3, json, os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from .tables import upload_table, create_table
from django.views.decorators.csrf import csrf_exempt
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .vectorize import process_chunks

def upload_image_to_s3(file, bucket, object_name=None, region="ap-south-1"):
    if object_name is None:
        object_name = file.name

    s3_client = boto3.client('s3', region_name=region)

    try:
        s3_client.head_bucket(Bucket=bucket)
        s3_client.upload_fileobj(file, bucket, object_name)
        print("FILE UPLOADED TO S3")
        return object_name
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except PartialCredentialsError:
        print("Incomplete credentials provided")
        return False
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket, CreateBucketConfiguration=location)

            s3_client.upload_fileobj(file, bucket, object_name)
            print("BUCKET CREATED SUCCESFULLY")
            print("FILE UPLOADED")
            return object_name
        else:
            print(f"Error checking bucket: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def extract_data_from_image(doc_name, region = "ap-south-1"):
    try:
        client = boto3.client('textract', region_name = region)
        response = client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': 'nurenai',
                    'Name': doc_name,
                }
            },
            FeatureTypes=['TABLES', 'FORMS']
        )
        data = json.dumps(response, indent=3)
        textract_data = json.loads(data)
        for block in textract_data['Blocks']:
            if block['BlockType'] == 'LINE':
                print("block : " ,block['Text'])
            
        return textract_data
    except Exception as e:
        return JsonResponse({"status" : 500, "message": f"Unable to extract data from table. Error occured: {e}"})

def convert_into_df(textract_data):
    try:
        # Extract cells from Textract data
        cells = [block for block in textract_data['Blocks'] if block['BlockType'] == 'CELL']
        
        table = {}
        for cell in cells:
            row = cell['RowIndex']
            col = cell['ColumnIndex']
            text = ''
            for relationship in cell.get('Relationships', []):
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        try:
                            text_block = next(block for block in textract_data['Blocks'] if block['Id'] == child_id)
                            if text_block['BlockType'] == 'WORD':
                                text += text_block['Text'] + ' '
                        except StopIteration:
                            print(f"Child block with ID {child_id} not found.")
                        except KeyError as e:
                            print(f"KeyError cdf: {e}")
        
            text = text.strip()
            if row not in table:
                table[row] = {}
            table[row][col] = text
        table_list = []
        for row_index in sorted(table.keys()):
            row = []
            for col_index in sorted(table[row_index].keys()):
                row.append(table[row_index][col_index])
            table_list.append(row)

        # # Optionally convert to a pandas DataFrame
        # result = "\n".join(["!".join(row) for row in table_list])
        # data = StringIO(result)
        # df = pd.read_csv(data, sep="!")
        
        return table_list
    
    except ClientError as e:
        print(f"ClientError: {e}")
        return None
    except KeyError as e:
        print(f"KeyError: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def convert_into_text(textract_data):
    try:
        cells = [block for block in textract_data['Blocks'] if block['BlockType'] == 'WORD']
        text=""
        for cell in cells:
            if cell['BlockType'] == 'WORD':
                text+=cell['Text']+" "
                

        return text
    except ClientError as e:
        print(f"ClientError: {e}")
        return None
    except KeyError as e:
        print(f"KeyError: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def upload_text_to_db(generated_text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    texts = text_splitter.split_text(generated_text)
    status = process_chunks(texts)
    return status

def delete_file(bucket, file, region= "ap-south-1"):
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.delete_object(Bucket=bucket, Key=file)
        print("Delete Successful")
        return True
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except ClientError as e:
        print(f"Error occurred: {e}")
        return False

@csrf_exempt
def data_from_image(request):
    try:
        if 'file' not in request.FILES:
            return JsonResponse({"status": 400, "message": "No file provided in the request"}, status=400)
        
        file = request.FILES['file']
        model_name = request.POST.get('model_name', None)
        table_name = request.POST.get('table_name', None)
        
        if table_name == None and model_name == None:
            table_name = os.path.splitext(file.name)[0].replace(' ','_').replace('-','_')
        elif model_name and table_name:
            return JsonResponse({"status": 400, "message": f"""Either of model_name or table_name must be provided, but not both.\nprovide model_name to upload table to database. \nprovide table_name to create a new table to database and upload data"""}, status=400)
         
        print("rcvd data with file and model name: " ,model_name, table_name)
        bucket = 'nurenai'
        file_name = 'upload.jpg'
        region = "ap-south-1"

        doc_name = upload_image_to_s3(file, bucket, file_name, region)
        # print("@",doc_name)

        textract_data = extract_data_from_image(doc_name)
        
        text, tables = extract(textract_data)
        print("table list: " ,tables)
        
        #if table_name is provided
        if table_name: 
            i=0
            for table in tables:
                t_name = table_name + f"_{i}"
                print(t_name)
                create_table(table, t_name)
                print("table created succesfully: " ,t_name)
                i+=1
        #if model_name is provided
        else:
            for table in tables:
                print("table: ", table)
                upload_table(table, model_name)
                print("table uploaded succesfully: " ,model_name)

        # if len(text)>0:        
        #     print("generated text: " ,text)
        #     upload_text_to_db(text)
        #     print("text uploaded succesfully")
            
            
        delete_file(bucket, file=file_name)

        

        return JsonResponse({"status": 200, "message": "File processed successfully"})
    
    except KeyError as e:
        return JsonResponse({"status": 400, "message": f"Key error: {e}"}, status=400)
    except NoCredentialsError:
        return JsonResponse({"status": 400, "message": "AWS credentials not available"}, status=400)
    except PartialCredentialsError:
        return JsonResponse({"status": 400, "message": "Incomplete AWS credentials provided"}, status=400)
    except boto3.exceptions.S3UploadFailedError:
        return JsonResponse({"status": 500, "message": "Failed to upload file to S3"}, status=500)
    except Exception as e:
        return JsonResponse({"status": 500, "message": f"Internal server error: {e}"}, status=500)


def extract(textract_data):
    try:
        blocks = textract_data.get('Blocks', [])
        word_dic = {}
        curr_table = []
        tables = []
        text = ""

        combined_list = []
        for block in blocks:
            print(block['BlockType'])
            try:
                if block['BlockType'] == 'WORD':
                    id = block['Id']
                    text = block['Text']
                    word_dic[id] = text
                
                elif block['BlockType'] == 'TABLE' or block['BlockType'] == 'TABLE_TITLE' or block['BlockType']== 'KEY_VALUE_SET':
                    if len(curr_table) != 0:
                        tables.append(curr_table)
                    curr_table = []

                elif block['BlockType'] == 'CELL':
                    print("cell block: ", block)
                    row = block['RowIndex']
                    column = block['ColumnIndex']
                    id = block['Relationships'][0]['Ids']
                    text = ""
                    for i in id:
                        combined_list.append(i)
                        text += word_dic[i] + " "
                    curr_table.append({"row": row, "column": column, "text": text})
                    print("curr table: ", curr_table)
            except Exception as e:
                print(f"Error processing block: {block}, Error: {e}")
                continue
        tables.append(curr_table)
        print("tables: ", tables)
        text = ""
        for block in blocks:
            try:
                if block['BlockType'] == 'WORD' and block['Id'] not in combined_list:
                    text += block['Text'] + " "
            except Exception as e:
                print(f"Error processing block: {block}, Error: {e}")
                continue

        formatted_tables = []
        for table in tables:
            rows = []
            for row_dict in table:
                try:
                    row_index = row_dict['row'] - 1
                    col_index = row_dict['column'] - 1
                    # Ensure the row exists in the list
                    while len(rows) <= row_index:
                        rows.append([])
                    # Ensure the column exists in the row
                    while len(rows[row_index]) <= col_index:
                        rows[row_index].append('')
                    # Set the value in the appropriate cell
                    rows[row_index][col_index] = row_dict['text']
                except Exception as e:
                    print(f"Error processing row: {row_dict}, Error: {e}")
                    continue
            formatted_tables.append(rows)
        print("FORMATTED TABLE: ", formatted_tables)
        print("TEXT: ", text)
        return text, formatted_tables
    except Exception as e:
        print(f"Error in extract function: {e}")
        return "", []