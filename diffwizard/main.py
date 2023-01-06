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
        diff = subprocess.check_output(["git", "diff", commit_1, commit_2, "--no-color"])
        diff = diff.decode("utf-8")
        print(diff)

        return diff

    def _get_model_result_from_diff(self, diff: str):

        explanation = """---
        The above diff is a diff of a commit. Please write a concise changelog for this commit.
        Please write the changelog in the following valid json format, and use the following template:
        { "added": ["Added a new feature x to file y", "Added a new feature a to file b"],
            "changed": ["Changed the way feature y works"],
        "removed": ["Removed feature z"]
        }
        """

        prompt = diff+explanation
        output = openai.Completion.create(
            model=self.model,
            prompt=prompt,
            max_tokens=self.max_tokens,

        )
        # Return the output, the diff, and the finish reason in a tuple
        results = (output.choices[0].text, diff, output.choices[0].finish_reason)
        if output.choices[0].finish_reason != "stop":
            print("WARNING: Model did not stop itself, please check the output")
        return results

    def _parse_diff(self, diff: str):
        """Parse a git diff into a list of files and changes
        """
        diff = diff.split("diff --git")
        diff = [i for i in diff if i != ""]
        return diff


    def _split_long_diff(self, diff: str, max_length: int = 2000):
        """Split a diff into multiple diffs of max_length, first on file, then on lines
        """
        if len(diff) < max_length:
            return [diff]
        # Split on files if diff too long
        diffs = self._parse_diff(diff)
        new_diffs = []
        for d in diffs:
            if len(d) > max_length:
                stop_index=0
                i=0
                while len(d) > max_length:
                    max_i = min((i+1)*max_length, len(d))
                    new_d = d[stop_index:max_i]
                    stop_index = new_d.rfind("/n")
                    new_d = new_d[:stop_index]
                    new_diffs.append(new_d)
                    i+=1
            else:
                new_diffs.append(d)
        return new_diffs

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

    def get_changelog(self, folder: str = os.getcwd(), commit_1: str = "HEAD~1", commit_2: str = "HEAD"):
        diff = self._get_diff(folder, commit_1, commit_2)
        diffs = self._split_long_diff(diff)
        results = []
        for d in diffs:
            results.append(self._get_model_result_from_diff(d))
        return self._parse_results(results)


if __name__ == "__main__":
    load_dotenv()
    dw = DiffWizard(api_key=os.environ["OPENAI_API_KEY"])
    print(dw.get_changelog())
