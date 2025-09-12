import os
import json
from google.cloud import speech
from dotenv import load_dotenv
from pathlib import Path
import tempfile
from pydub import AudioSegment
import uuid

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

# Suporte para GOOGLE_APPLICATION_CREDENTIALS_JSON (para deploy seguro)
if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        f.write(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON").encode())
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
else:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


class TranscritorGoogle:
    def __init__(self):
        self.client = speech.SpeechClient()

    def convert_to_ogg(self, input_path: str) -> (str, int, int):
        output_path = f"/tmp/{uuid.uuid4().hex}.ogg"
        audio = AudioSegment.from_file(input_path)

        audio = audio.set_channels(1).set_frame_rate(16000)

        audio.export(output_path, format="ogg", codec="libopus")

        return output_path, 16000, 1


    def transcrever(self, caminho_audio: str, saida_json: str = "transcricao.json") -> dict:
        ogg_path, sample_rate, channels = self.convert_to_ogg(caminho_audio)

        try:
            with open(ogg_path, "rb") as f:
                conteudo = f.read()

            audio = speech.RecognitionAudio(content=conteudo)

            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                sample_rate_hertz=sample_rate,
                language_code="pt-BR",
                model="latest_short",
                audio_channel_count=channels,
                enable_word_confidence=True,
                enable_word_time_offsets=True
            )

            operation = self.client.long_running_recognize(config=config, audio=audio)

            print("Aguardando a conclusão da transcrição...")
            response = operation.result(timeout=180)

            resultados = []
            for resultado in response.results:
                alternativas = []
                for alt in resultado.alternatives:
                    alternativas.append({
                        "transcricao": alt.transcript,
                        "confianca": alt.confidence,
                        "palavras": [
                            {
                                "texto": w.word,
                                "inicio": w.start_time.total_seconds(),
                                "fim": w.end_time.total_seconds(),
                                "confianca": getattr(w, "confidence", None),
                            }
                            for w in alt.words
                        ]
                    })
                resultados.append({"alternativas": alternativas})

            with open(saida_json, "w", encoding="utf-8") as f:
                json.dump({"resultados": resultados}, f, ensure_ascii=False, indent=2)

            print(f"Transcrição salva em {saida_json}")
            return {"resultados": resultados}

        finally:
            if os.path.exists(ogg_path):
                os.remove(ogg_path)


if __name__ == "__main__":
    resultado = TranscritorGoogle().transcrever("audio_process/audios/1928037095_245.ogg", "transcricao.json")
    print(resultado)
