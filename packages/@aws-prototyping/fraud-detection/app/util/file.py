def format_file_size(size):
    """
    Formats the given file size in bytes to a human-readable string.

    Args:
        size (int): The file size in bytes.

    Returns:
        str: A string representing the file size in a human-readable format.
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size_float = float(size)

    while size_float >= 1024 and unit_index < len(units) - 1:
        size_float /= 1024.0
        unit_index += 1

    return "{:.2f} {}".format(size_float, units[unit_index])
