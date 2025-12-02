def model_name_format(item):
    item = item['name'].replace(' (free)', '').split(': ')
    if len(item) > 1:
        return f'{item[1]}, di {item[0]}'
    else: 
        return item[0]