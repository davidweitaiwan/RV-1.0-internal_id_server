import os
import glob
import shutil
import re
import datetime

def merge_files(directory, ext='.bin'):
    # Search for all files
    files = glob.glob(os.path.join(directory, '*' + ext))

    # Create a regex pattern to check filenames
    pattern = re.compile(r'\d{17}' + re.escape(ext) + r'$')

    # Filter out the files with the correct format
    filtered_files = [f for f in files if pattern.search(os.path.basename(f))]

    # If filtered_files is empty, return directly
    if not filtered_files:
        return

    # Parse filenames to time and sort
    sorted_files = sorted(filtered_files, key=lambda x: int(os.path.basename(x).split('.')[0]))

    # Initialize a list to store file groups
    file_groups = []
    current_group = [sorted_files[0]]

    # Iterate through each file, if the time gap exceeds 2 seconds then create a new group
    for i in range(1, len(sorted_files)):
        current_file = sorted_files[i]
        last_file = current_group[-1]
        current_time = datetime.datetime.strptime(os.path.basename(current_file)[:-4], '%Y%m%d%H%M%S%f')
        last_time = datetime.datetime.strptime(os.path.basename(last_file)[:-4], '%Y%m%d%H%M%S%f')

        if (current_time - last_time).total_seconds() > 2:
            file_groups.append(current_group)
            current_group = [current_file]
        else:
            current_group.append(current_file)

    # Append the last group
    file_groups.append(current_group)

    # Iterate through each group to merge files
    for group in file_groups:
        if len(group) > 1:
            # The file with the maximum timestamp in the group
            max_file = max(group, key=os.path.getctime)
            # Temporary file for merging
            temp_file_name = os.path.join(directory, 'temp' + ext)

            # Open the temporary file and write data
            with open(temp_file_name, 'wb') as outfile:
                for fname in sorted(group, key=os.path.getctime):  # Ensure that the files are merged in time order
                    with open(fname, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)

            # Rename the temporary file to the file with the maximum timestamp
            new_file_name = os.path.join(directory, os.path.basename(max_file))
            os.rename(temp_file_name, new_file_name)

            # Delete the original files
            for fname in group:
                if fname != max_file:  # Do not delete the file with the maximum timestamp
                    os.remove(fname)

# Call this function with the directory path as the argument
merge_files('/home/pi/')
