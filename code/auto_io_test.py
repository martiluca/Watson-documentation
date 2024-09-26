#!/usr/bin/env python3

# Import modules
import argparse
import os
import csv
import time
import ruamel.yaml
import glob
import subprocess

# Import custom functions
from reanaming import RenameFiles


### --- ARGUMENT PARSER --- ###
parser = argparse.ArgumentParser(
    description="Python wrapper for launching the pipeline analysis. Put the Runs folders in the input directory and run the script: it will automatically launch the pipeline in each folder."
)

parser.add_argument(
    "-t",
    "--threads",
    type=int,
    required=False,
    help="Number of threads to run snakemake. Default = 39. Note: bcl2fastq requires at least 16 threads.",
)


args = parser.parse_args()

T = args.threads

### --- CONFIG FILE AND SAMPLE INFO COMPILATION --- ###
# Static files
static_path = "/home/watson/snakemake_watson/static_files"
bin_path = "/home/watson/snakemake_watson/bin"
reference_path = "/home/watson/snakemake_watson/static_files/GRCh38.fa"
output_path = "/home/watson/snakemake_watson/output"

# Get runs
input_dir = "/home/watson/snakemake_watson/input"
run_names = []
input_contents = os.listdir(input_dir)
for item in input_contents:
    if os.path.isdir(os.path.join(input_dir, item)) and os.path.join(
        input_dir, item
    ) != os.path.join(input_dir, "__pycache__"):
        run_names.append(item)

for run in run_names:
    run_path = os.path.join(input_dir, run)
    output_run = os.path.join(output_path, run)

    ### --- Write sample_info.csv --- ###
    sample_sheet_path = os.path.join(run_path, "LIMS_supp_sample_sheet.csv")
    sample_info = os.path.join(run_path, "sample_info.csv")

    with open(sample_sheet_path, "r") as source:
        reader = csv.reader(source)

        with open(sample_info, "w") as result:
            writer = csv.writer(result)
            for r in reader:
                writer.writerow((r[0], r[7], r[10], r[11]))

    ### --- Write config file --- ###
    config_path = os.path.join(run_path, "config.yaml")

    data = {
        "STATIC_FILES_DIR": f'"{static_path}"',
        "BIN_DIR": f'"{bin_path}"',
        "OUTPUT_DIR": f'"{output_run}"',
        "REFERENCE": f'"{reference_path}"',
        "SAMPLE_INFO_FILE": f'"{sample_info}"',
        "SAMPLE_DIR": f'"{run_path}"',
    }

    # Write run to config
    with open(config_path, "w") as config_file:
        for entry in data:
            config_file.write(f"{entry}: {data[entry]}\n")

### --- RUN PIPELINE OVER ALL DIRS IN INPUT DIR --- ###
for run in run_names:
    print(f"\nPreparing to start analysis on {run}")
    run_path = os.path.join(input_dir, run)
    config_path = os.path.join(run_path, "config.yaml")

    print(f"Reading {config_path}")
    with open(config_path, "r") as config_file:
        data = ruamel.yaml.load(config_file, Loader=ruamel.yaml.RoundTripLoader)
        FASTQ_DIR = os.path.join(data.get("SAMPLE_DIR"), "FASTQ_files")
        OUTPUT_DIR = data.get("OUTPUT_DIR")

    # Rename samples
    print("Renaming and concatenating files...")
    FileListDir = os.path.join(FASTQ_DIR, "FASTQ_file_list.csv")
    with open(FileListDir, "r") as FileList:
        reader = csv.DictReader(FileList)

        # Dictionaries to handle file names
        DictR1 = {}
        DictR2 = {}

        for row in reader:
            RunId = row["LIMS_ID"]
            FileNameR1 = row["Filename_R1"]
            FileNameR2 = row["Filename_R2"]

            # Rename and concatenate files
            RenameFiles(FASTQ_DIR, RunId, FileNameR1, DictR1, "R1")
            RenameFiles(FASTQ_DIR, RunId, FileNameR2, DictR2, "R2")

    print("DONE!")

    ### --- Add samples to config --- ###
    samples_paths = glob.glob(FASTQ_DIR + "/Run*_R1.fastq.gz")

    samples_names = [path.split("/")[-1].split("_")[0] for path in samples_paths]
    samples_paths = [FASTQ_DIR + f"/{path}" for path in samples_names]

    # Write runs to config
    print("Writing samples to config...")
    with open(config_path, "a") as config_file:
        config_file.write("SAMPLES:\n")
        for path, name in zip(samples_paths, samples_names):
            config_file.write(f'  {name}: "{path}"\n')
    print("DONE!")

    ### --- Start pipeline --- ###
    print("\nStarting analysis on {run}")

    conda_path = "/home/watson/anaconda3/etc/profile.d/conda.sh"
    conda_activation = f"source {conda_path} && conda activate snakemake"
    snakemake_activation = (
        f"snakemake -j {T} --configfile {config_path}"
        + " --cluster \"sbatch --job-name='{params.sampleID} {rule}' --partition={params.partition} --output={params.logfile} --cpus-per-task={params.cpus_per_task} --mem={params.mem} --parsable\" &"
    )

    subprocess.call(conda_activation, shell=True, executable="/bin/bash")
    subprocess.call(snakemake_activation, shell=True, executable="/bin/bash")

    starttime = time.time()
    while (
        os.path.isfile(os.path.join(OUTPUT_DIR, "log", "000-pipeline_completed"))
        == False
    ):
        print(f"{time.ctime()} - Pipeline is still running...")
        time.sleep(1200 - ((time.time() - starttime) % 1200))
    print("PIPELINE COMPLETED!")

### --- FINAL CLEANUP --- ### -> Remove unnecessary files, move to output directory and archive
for run in run_names:
    run_path = os.path.join(input_dir, run)
    config_path = os.path.join(run_path, "config.yaml")

    ### --- Move results to output directory --- ###
    


