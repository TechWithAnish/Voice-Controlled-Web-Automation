import openai

from config import apikey

openai.api_key = apikey

response = openai.Completion.create(
  model="text-davinci-003",
  prompt="Write an email to my boss for resignation\n",
  temperature=0.7,
  max_tokens=256,
  top_p=1,
  frequency_penalty=0,
  presence_penalty=0
)

print(response)
'''
{
  "id": "cmpl-7ZK6YYhFGlKhVfkFPQvIbz0hIsl6I",
  "object": "text_completion",
  "created": 1688653118,
  "model": "text-davinci-003",
  "choices": [
    {
      "text": "\n\nSubject: Resignation\n\nDear [Boss Name],\n\nI am writing to inform you that I am resigning from my position at [Company Name]. This decision has been difficult for me, but I have decided that it is the best course of action for me at this time.\n\nI have had a very positive experience working with [Company Name] and have thoroughly enjoyed my time here. I would like to thank you for the opportunity to work here and the support you have given me over the past [x] years.\n\nI am available to help with the transition in any way possible. Please let me know if there is anything I can do to make the process smoother.\n\nThank you again for the opportunity.\n\nSincerely,\n[Your Name]",
      "index": 0,
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 162,
    "total_tokens": 171
  }
}
'''