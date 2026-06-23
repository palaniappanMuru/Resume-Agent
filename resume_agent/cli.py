import argparse
import json

from resume_agent.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="resume_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the full JD-to-resume pipeline")
    run_parser.add_argument("--jd", required=True, help="Path to a JD text/PDF file, or raw JD text")

    args = parser.parse_args()

    if args.command == "run":
        result = run_pipeline(args.jd)
        print(f"Job Role: {result['job_role_name']}")
        print("ATS Report:")
        print(json.dumps(result["ats_report"].model_dump(), indent=2))
        print("JD Match Status:")
        print(json.dumps(result["jd_match_status"].model_dump(), indent=2))
        if result["jd_match_status"].matched:
            print(f"JSON:  {result['json_path']}")
            print(f"DOCX:  {result['docx_path']}")
        else:
            print("Resume not generated: ATS score below threshold.")


if __name__ == "__main__":
    main()
