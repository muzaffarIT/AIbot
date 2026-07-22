"""Voice integrations (speech-to-text / text-to-speech).

Routes through KIE.ai's ElevenLabs models today via the same async
createTask → recordInfo flow as image/video generation. Swapping to a direct
provider later only means adding a client here.
"""
