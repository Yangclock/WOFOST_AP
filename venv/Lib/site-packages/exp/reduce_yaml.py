from pathlib import Path


def process_yaml_file(fname):

    out_fname = fname.with_suffix(".yaml.new")
    lines_out = []
    
    weather_section = False
    weather_valid_period = False
    with open(fname) as fp_read:
        for line in fp_read:
            if not weather_section:
                lines_out.append(line)
            else: 
                if weather_valid_period:
                    lines_out.append(line)

            if line.startswith("WeatherVariables:"):
                weather_section = True

            if line.startswith("- DAY: 1982-01-01"):
                weather_valid_period = True
                lines_out.append(line)
            
            if line.startswith("- DAY: 1987-01-02"):
                weather_valid_period = False
                lines_out.pop(-1)
   
    with open(fname, "w") as fp_out:
        fp_out.writelines(lines_out)
            

def main():
    this_dir = Path.cwd()
    for fname in this_dir.glob("*.yaml"):
        print(f"processing {fname.name}")
        process_yaml_file(fname)


if __name__ == "__main__":
    main()

