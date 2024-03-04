def extract_first_if_tuple(data_list):
    return [item[0] if isinstance(item, tuple) else item for item in data_list]