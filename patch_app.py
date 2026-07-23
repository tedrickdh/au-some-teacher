from pathlib import Path
import re
import shutil
import sys

APP_FILE = Path("frontend/src/App.js")

GOOGLE_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbxB1fXiDyfEPSgySoJg7RAIxWTDoPRwKOPzZu7VZWXR3KZodJ7-cu3bSkE8rzJfqw6h/exec"
)

if not APP_FILE.exists():
    print(f"ERROR: Could not find {APP_FILE}")
    print("Run this script from the main au-some-teacher project folder.")
    sys.exit(1)

backup_file = APP_FILE.with_suffix(".js.backup")
shutil.copy2(APP_FILE, backup_file)

text = APP_FILE.read_text(encoding="utf-8")

# Remove the Axios import.
text = re.sub(
    r'^\s*import axios from ["\']axios["\'];\s*\n',
    "",
    text,
    flags=re.MULTILINE,
)

# Replace the old backend constants.
old_constants_pattern = re.compile(
    r'const BACKEND_URL\s*=\s*process\.env\.REACT_APP_BACKEND_URL;\s*\n'
    r'const API\s*=\s*`\$\{BACKEND_URL\}/api`;\s*\n'
)

new_constants = (
    'const GOOGLE_SCRIPT_URL =\n'
    f'  "{GOOGLE_SCRIPT_URL}";\n'
)

text, constants_count = old_constants_pattern.subn(
    new_constants,
    text,
    count=1,
)

if constants_count == 0:
    # Add the Google URL after the imports if the old constants
    # have already been removed.
    if "const GOOGLE_SCRIPT_URL" not in text:
        import_matches = list(
            re.finditer(r"^import .*?;\s*$", text, flags=re.MULTILINE)
        )

        if import_matches:
            insert_at = import_matches[-1].end()
            text = (
                text[:insert_at]
                + "\n\n"
                + new_constants.rstrip()
                + text[insert_at:]
            )
        else:
            print("ERROR: Could not determine where to add GOOGLE_SCRIPT_URL.")
            sys.exit(1)

new_function = r'''function useLeadForm(kind) {
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(emptyLeadForm);

  const update = (event) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const submit = async (event) => {
    event.preventDefault();

    if (submitting) {
      return;
    }

    setSubmitting(true);

    try {
      const payload = {
        kind,
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        child_age: form.child_age.trim(),
        insurance: form.insurance.trim(),
        city: form.city.trim(),
        message: form.message.trim(),
      };

      await fetch(GOOGLE_SCRIPT_URL, {
        method: "POST",
        mode: "no-cors",
        headers: {
          "Content-Type": "text/plain;charset=utf-8",
        },
        body: JSON.stringify(payload),
      });

      toast.success("Thank you — your message was received.", {
        description: "Our team will follow up with next steps soon.",
      });

      setForm({ ...emptyLeadForm });
    } catch (error) {
      console.error("Google Apps Script submission failed:", error);

      toast.error("We couldn't send the form yet.", {
        description:
          "Please try again or email info@au-someteacher.com.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return {
    form,
    submitting,
    update,
    submit,
  };
}'''

function_pattern = re.compile(
    r"function useLeadForm\(kind\) \{.*?\n\}\n\n(?=function LeadTextField)",
    flags=re.DOTALL,
)

text, function_count = function_pattern.subn(
    new_function + "\n\n",
    text,
    count=1,
)

if function_count == 0:
    print("ERROR: Could not find the useLeadForm function.")
    print(f"Your original file was saved as {backup_file}")
    sys.exit(1)

APP_FILE.write_text(text, encoding="utf-8")

print("")
print("SUCCESS: App.js was updated.")
print(f"Updated file: {APP_FILE}")
print(f"Backup file:  {backup_file}")
print("")
print("The form now submits to Google Apps Script.")
