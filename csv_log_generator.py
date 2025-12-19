import os
import pandas as pd
import argparse
import numpy as np
from ldparser.ldparser import ldData

def ld_to_resampled_csv(ld_filepath, csv_output_path):
    print(f"Reading MoTeC file: {ld_filepath}")
    ld_log = ldData.fromfile(ld_filepath) #
    
    channels_dict = {}
    max_freq = 0
    master_channel_name = None

    # Extract data and find the highest sample rate
    for chan in ld_log.channs: #
        name = chan.name
        freq = chan.freq #
        data = chan.data #
        
        # Calculate individual time axis: Time = Index * (1 / Frequency)
        time_axis = np.arange(len(data)) / freq
        channels_dict[name] = pd.Series(data, index=time_axis)
        
        if freq > max_freq:
            max_freq = freq
            master_channel_name = name

    print(f"Resampling all channels to {max_freq}Hz (based on '{master_channel_name}')")
    print(ld_log.head)
    df = pd.DataFrame(channels_dict)
    
    # Sort index to ensure temporal continuity for interpolation
    df = df.sort_index()
    
    # Reindex to the master timebase (the timestamps of the fastest channel)
    master_time = channels_dict[master_channel_name].index
    final_df = df.reindex(master_time)

    # cull data that is before and after car running (RPM != 0)
    if 'Car Data Motor MotorRPM' in final_df.columns:
        non_zero_rpm_indices = final_df.index[(final_df['Car Data Motor MotorRPM'] != 0) & (final_df['Car Data Motor MotorRPM'].notnull())]
        if not non_zero_rpm_indices.empty:
            first_non_zero_rpm_index = max(0, non_zero_rpm_indices[0] - 1)  # 1 second after
            print(f"Trimming data to start from index: {first_non_zero_rpm_index}")
            final_df = final_df.loc[first_non_zero_rpm_index:]
            # last non zero rpm
            last_non_zero_rpm_index = min(len(final_df), non_zero_rpm_indices[-1] + 1)  # 1 second after
            final_df = final_df.loc[:last_non_zero_rpm_index]
            print(f"Trimming data to end at index: {last_non_zero_rpm_index}")

    # export to ld_log.head.short_comment csv
    if hasattr(ld_log.head, 'short_comment') and ld_log.head.short_comment:
        short_comment = ld_log.head.short_comment
        # check for existing file
        base, ext = os.path.splitext(csv_output_path)
        csv_output_path = f"{base}_{short_comment}{ext}"
        print(f"Appending short comment to filename: {csv_output_path}")

    final_df.index.name = 'Time_s'
    final_df.to_csv(csv_output_path)
    print(f"Successfully exported to: {csv_output_path}")


if __name__ == "__main__":
    # ld_to_resampled_csv("autox_run1.ld", "test.csv")
    # # parser
    parser = argparse.ArgumentParser(description="Convert MoTeC .ld files to resampled CSV format.")
    parser.add_argument("--input-folder", help="Path to the input folder")
    parser.add_argument("--output-folder", help="Path to the output folder")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    for filename in os.listdir(input_folder):
        if filename.endswith(".ld"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename[:-2] + "csv")
            ld_to_resampled_csv(input_path, output_path)