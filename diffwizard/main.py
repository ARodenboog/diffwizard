from datetime import datetime
import subprocess
import os
import json
import openai
from dotenv import load_dotenv

class DiffWizard:

    def __init__(self, api_key: str = None, model: str = "text-davinci-003", max_tokens: int = 500):
        load_dotenv()
        if api_key is None:
            api_key = os.environ["OPENAI_API_KEY"]
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        openai.api_key = self.api_key

    def _get_diff(self, folder: str, commit_1: str, commit_2: str):
        """Get the diff between two different commits
        """
        os.chdir(folder)
        diff = subprocess.check_output(["git", "diff", commit_1, commit_2])
        diff = diff.decode("utf-8")
        return diff

    def _get_model_result_from_diff(self, diff: str):

        explanation = """---
        The above diff is a diff of a commit.
        You are a developer and you need to write a concise changelog for this commit.
        Please write the changelog in the following valid json format, and use the following template:
        { "added": [],
        "changed": [],
        "removed": []
        }
        Put the changes in the appropriate lists, surrounded by quotes and separated by commas.
        Be sure to include the file name in the change description, if applicable. Please stay to the point.
        If the commit does not contain meaningful changes, please leave the lists empty.
        """
        # Hack: If diff is too short, return default
        # Without this, the model will return a random changelog
        if len(diff) <30:
            default = """{ "added": [],
                "changed": [],
                "removed": []
                }"""
            return (default, diff, "stop")
        prompt = diff+explanation
        try:
            output = openai.Completion.create(
                model=self.model,
                prompt=prompt,
                max_tokens=self.max_tokens,

            )
        except openai.error.ServiceUnavailableError as e:
            print("ERROR: OpenAI service unavailable, please try again later")
            raise e
        # Return the output, the diff, and the finish reason in a tuple
        results = (output.choices[0].text, diff, output.choices[0].finish_reason)
        if output.choices[0].finish_reason != "stop":
            print("WARNING: Model did not stop itself, please check the output")
        return results

    def _split_long_diff(self, diff: str, max_length: int = 2000):
        """Split a diff into multiple diffs of no longer than max_length, first on file, then on lines
        """
        # If diff is short enough, return it
        if len(diff) < max_length:
            return [diff]
        # Split on files if diff too long
        file_index = diff[:max_length].rfind("diff --git")
        # If resulting diff is too short, split on lines
        if file_index == -1 or file_index < max_length/4:
            file_index = diff[:max_length].rfind("\n")
            if file_index == -1:
                file_index = max_length
        diff_1 = diff[:file_index]
        diff = diff[file_index:]
        return [diff_1] + self._split_long_diff(diff, max_length)

    def _parse_output(self, output: str):
        start_index = output.find("{")
        end_index = output.rfind("}")
        output = output[start_index:end_index+1]
        if output == "":
            print("ERROR: Empty output")
            return None
        try:
            return json.loads(output)
        except Exception as e:
            print(f"ERROR: {e} ")
            return None

    def _parse_results(self, results: list):
        mdict = {"changed": [], "added": [], "removed": []}
        for result in results:
            output = result[0]
            vals = self._parse_output(output)
            if vals is None:
                continue
            if "added" in vals.keys():
                mdict["added"].extend(vals["added"])
            if "removed" in vals.keys():
                mdict["removed"].extend(vals["removed"])
            if "changed" in vals.keys():
                mdict["changed"].extend(vals["changed"])
        return mdict

    def _get_result_summary_from_model(self, result: dict):
        result = json.dumps(result)
        explanation: str = """---
        The above is a changelog in json format.
        Please write a summary of the changelog in bullet points, separated by newlines.
        """
        try:
            summary = openai.Completion.create(
                model=self.model,
                prompt=result+explanation,
                max_tokens=self.max_tokens,
            )
        except openai.error.ServiceUnavailableError as e:
            print("ERROR: OpenAI service unavailable, please try again later")
            raise e
        return summary.choices[0].text

    def get_changelog(self, folder: str = os.getcwd(), commit_1: str = "HEAD~1", commit_2: str = "HEAD"):
        diff = self._get_diff(folder, commit_1, commit_2)
        diffs = self._split_long_diff(diff)
        results = []
        for d in diffs:
            results.append(self._get_model_result_from_diff(d))

        mdict = self._parse_results(results)
        with open(os.path.join(folder, "changelog.json"), "r") as f:
            current = json.load(f)
        current[datetime.now().isoformat()] = mdict
        with open(os.path.join(folder, "changelog.json"), "w") as f:
            json.dump(current, f)
        summary = self._get_result_summary_from_model(mdict)
        with open(os.path.join(folder, "changelog.md"), "a") as f:
            f.write(summary)
        return mdict, summary


if __name__ == "__main__":
    load_dotenv()
    dw = DiffWizard(api_key=os.environ["OPENAI_API_KEY"])
    print(dw.get_changelog())
