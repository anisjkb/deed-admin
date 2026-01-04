def generate_report(format: str = "pdf"):
    path = f"reports/report.{format}"
    with open(path, "w") as f:
        f.write(f"Sample {format.upper()} Report")
    return path
