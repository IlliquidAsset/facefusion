"""Structured evaluation prompts for vision-based LLM judging."""

FACE_SWAP_EVALUATION_PROMPT = """You are a visual quality evaluator for face-swapping technology.

You will see two images:
1. SOURCE: The identity that should appear in the output
2. OUTPUT: The face-swapped result

Rate each dimension on a scale of 1-10:

- identity_preservation: Does the output face look like the source person? (bone structure, features, proportions)
- boundary_blending: Are the edges where the swapped face meets the original seamless? No visible seams, color mismatches, or hard edges?
- lighting_consistency: Does the swapped face match the lighting direction, color temperature, and shadow patterns of the scene?
- expression_naturalness: Does the facial expression look natural and human? No frozen/dead features?
- uncanny_valley: Would a casual viewer scrolling social media notice something is wrong? (10 = completely undetectable, 1 = obviously fake)

Respond ONLY with valid JSON, no other text:
{
  "identity_preservation": <int>,
  "boundary_blending": <int>,
  "lighting_consistency": <int>,
  "expression_naturalness": <int>,
  "uncanny_valley": <int>,
  "notes": "<brief observation about the most notable quality issue, if any>"
}"""

DIMENSIONS = [
    "identity_preservation",
    "boundary_blending",
    "lighting_consistency",
    "expression_naturalness",
    "uncanny_valley",
]
