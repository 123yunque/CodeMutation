with open(inputs_file, 'w', encoding='utf-8') as f:
    for item in inputs:
        f.write(str(item) + "\n")

# 写 results，每项一行
with open(results_file, 'w', encoding='utf-8') as f:
    for item in result:
        f.write(str(item) + "\n")