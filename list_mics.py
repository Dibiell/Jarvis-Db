import speech_recognition as sr

def list_microphones():
    print("--- Microfones Detectados ---")
    mics = sr.Microphone.list_microphone_names()
    for i, name in enumerate(mics):
        print(f"Índice {i}: {name}")
    print("-----------------------------")

if __name__ == "__main__":
    list_microphones()
