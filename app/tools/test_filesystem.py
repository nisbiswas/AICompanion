from .filesystem import FileSystemTool


tool = FileSystemTool(
    r"C:\Users\admin\Documents\kafkaclone"
)

print("Files:")
print(tool.list_directory())

print("\n--- consumer.py ---")

content = tool.read_file("consumer.py")

print(content)