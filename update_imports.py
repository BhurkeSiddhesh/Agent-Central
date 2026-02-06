import sys

file_path = 'agency-hq/skills/voice-ai-engine-development/templates/multi_provider_factory_template.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
imported = False

for line in lines:
    if "class TranscriberProvider(ABC):" in line:
        skip = True

    if skip and "class VoiceComponentFactory:" in line:
        skip = False
        new_lines.append("from .interfaces import TranscriberProvider, LLMProvider, TTSProvider\n\n\n")
        new_lines.append("# ============================================================================\n")
        new_lines.append("# Multi-Provider Factory\n")
        new_lines.append("# ============================================================================\n\n")
        new_lines.append(line)
        continue

    if not skip:
        # remove the lines that are part of the interface block before TranscriberProvider
        if "Provider Interfaces" in line or (line.strip() == "# ============================================================================" and not imported):
             # We want to keep the first separator but maybe replace the block
             pass
        else:
             new_lines.append(line)

# The logic above is a bit brittle. Let's do a cleaner replacement.
# We know the content we want to remove.

content = "".join(lines)
start_marker = "# ============================================================================\n# Provider Interfaces\n# ============================================================================"
end_marker = "# ============================================================================\n# Multi-Provider Factory\n# ============================================================================"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + "from .interfaces import TranscriberProvider, LLMProvider, TTSProvider\n\n\n" + content[end_idx:]
    with open(file_path, 'w') as f:
        f.write(new_content)
    print("Successfully updated imports.")
else:
    print("Could not find markers.")
