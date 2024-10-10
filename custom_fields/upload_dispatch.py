from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest,JsonResponse
import os, pandas as pd,json, requests

def create_subfile(df, columns_text, merge_columns):
    print("DataFrame columns: ", df.columns)

    def get_column_names(df, indices):
        return [df.columns[i] for i in indices]

    df_new = df.copy()   

    if merge_columns:
        try:
            merge_columns_dict = json.loads(merge_columns)  
            print("Merge columns dict: ", merge_columns_dict)

            for new_col, indices in merge_columns_dict.items():
                desc = False
                if indices[0] == "desc":
                    desc = True
                    indices = indices[1:]  
                    
                if len(indices) < 2:
                    return JsonResponse({'error': 'Merge columns should be a list of at least two indices'}, status=400)

                try:
                    columns = get_column_names(df, indices)
                    if desc:
                        df_new[new_col] = df_new[columns].apply(
                            lambda x: ', '.join([f'{col}: {val}' for col, val in zip(columns, x)]), axis=1)
                    else:
                        df_new[new_col] = df_new[columns].astype(str).agg(', '.join, axis=1)

                    print(f"New column '{new_col}':", df_new[new_col])
                except IndexError:
                    return JsonResponse({'error': 'One or more column indices are out of range'}, status=400)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            return JsonResponse({'error': 'Invalid JSON format for merge_columns'}, status=400)
        except Exception as e:
            print("Exception:", e)
            return JsonResponse({'error': str(e)}, status=400)

    if columns_text:
        try:
            columns_dict = json.loads(columns_text)
            print("Columns dict:", columns_dict)

            columns_dict_with_names = {}
            for old_index, new_name in columns_dict.items():
                try:
                    old_col = df.columns[int(old_index)]
                    columns_dict_with_names[old_col] = new_name
                except IndexError:
                    return JsonResponse({'error': f'Column index {old_index} is out of range'}, status=400)

            
            df_new = df_new.rename(columns=columns_dict_with_names)

            
            df_new = df_new[list(columns_dict.values()) + (list(merge_columns_dict.keys()) if merge_columns else [])]

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            return JsonResponse({'error': 'Invalid JSON format for columns'}, status=400)
        except KeyError as e:
            print("KeyError:", e)
            return JsonResponse({'error': f'Column {e} not found in the input file'}, status=400)
        except Exception as e:
            print("Exception:", e)
            return JsonResponse({'error': str(e)}, status=400)
    else:
        
        df_new = df

    print("Final DataFrame created")
    return df_new