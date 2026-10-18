# Local Speech-to-Text for Noisy Voice Notes

**Practice notes from one deployment, measured on one person's own voice notes. Not a benchmark.**

Hermes transcribes incoming voice messages (Telegram voice notes and similar) before the agent sees them. This guide covers why one long-running setup replaced local Whisper with NVIDIA Parakeet, the numbers behind that choice, the shape of the new service, and how to repeat the test on your own recordings. Check the [official STT documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/tts) for the provider options and config keys of your version.

## 1. The problem

The owner records voice notes in public places: streets, cafés, transit. With Whisper large-v3-turbo running locally (faster-whisper, CPU, int8), transcripts of noisy notes lost words, and sometimes the model added a sentence nobody said at the end of a note. The agent then works from a transcript that is quietly wrong.

Constraints that shaped the choice:

- Languages: mostly Russian with English technical terms, sometimes English or German.
- Privacy: the notes are personal. Cloud STT providers differ in whether they train on submitted audio by default and how long they keep it; zero-retention options are often enterprise-only. Read the current terms before sending private audio anywhere. This setup stays fully local.
- Hardware: one always-on mini PC, an 8-core Zen 4 CPU with about 30 GB of usable RAM and an integrated GPU, shared with everything else the agent runs.

## 2. The test

Fifteen of the owner's own cached voice notes (16.4 minutes in total) were transcribed on the same box by six models. All ran locally; no audio left the machine.

- **Selection.** A rough noise estimate per note: the gap between loud and quiet 25 ms frames (90th minus 10th percentile, in dB; lower means noisier). The ten noisiest and five cleanest notes of 4–240 s were kept. One note was English; the rest Russian with English terms; none German.
- **Runtimes.** Whisper ran in faster-whisper inside the Hermes image, as in production. The others ran on [transcribe.cpp](https://github.com/handy-computer/transcribe.cpp), a ggml runtime with CPU and Vulkan backends that loads GGUF conversions of many ASR models.
- **Timing** includes loading the model for every note, because the old setup started a new process per voice note.
- **No reference transcripts.** Nobody hand-transcribed the notes. The comparison is word counts plus reading the transcripts side by side against the audio. That catches dropped and invented speech; it does not give a word error rate.

| Model | Size / quantization | Speed (x real time) | Median per note | Words, noisiest note (104 s) | Words, all 15 notes |
|---|---|---|---|---|---|
| Whisper large-v3-turbo, beam 3 (old setup) | int8 | 2.9x | 22.4 s | 72 | 1736 |
| Whisper large-v3, beam 5 | int8 | 1.5x | 40.0 s | 86 | 1741 |
| **Parakeet TDT 0.6B v3** | Q8_0 | **15.1x** | **3.8 s** | **169** | **1846** |
| Qwen3-ASR 1.7B | Q8_0 | 2.3x | 24.1 s | 86 | 1774 |
| Voxtral Mini 4B Realtime | Q6_K | 0.8x | 66.6 s | 97 | 1738 |
| GigaAM v3 (Russian only) | Q8_0 | 18.6x | 3.4 s | 174 | 1822 |

On the integrated GPU (Vulkan, three notes only) Parakeet reached 22.7x, Qwen3-ASR 4.0x, Voxtral 1.2x.

## 3. What the numbers say

- **Noise is where the models split.** On the noisiest note, Whisper turbo kept 72 words and ended with an invented "to be continued" line; Whisper large-v3, Qwen3-ASR and Voxtral kept 86–97. Parakeet and GigaAM kept the whole note (169 and 174 words). On the other fourteen notes all models were within a few words of each other.
- **One truly noisy note is a small sample.** The direction matches published results on crowd-sourced recordings (CoVoST), where Parakeet v3 beats Whisper large-v3 on English, German and Russian. On clean read speech (FLEURS) Whisper large-v3 is slightly better. If your recordings are clean, Whisper may be fine.
- **Speed.** Parakeet is about five times faster than the old turbo setup even with a cold start per note. Kept loaded, a 104 s note takes about 5 s.
- **GigaAM** is excellent on Russian but garbled the English note, so it needs language routing. **Qwen3-ASR** made more word errors on names and terms. **Voxtral** read well but runs slower than real time on this CPU.

Speech enhancement (denoising) before ASR was not tried: published results show it usually hurts modern ASR models, which are trained on noisy audio.

**Follow-up with references.** After the switch, the owner hand-corrected Parakeet's transcripts of five notes (15–139 s, picked across the noise range). Parakeet's word error rate against them is 1.2% overall and 0–2.4% per note, highest on the noisiest note. The corrections started from Parakeet's own output, so the number flatters Parakeet and cannot rank the other models. It serves as the baseline for judging the next model change.

## 4. What this setup runs now

[Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) (NVIDIA, CC-BY-4.0; 25 European languages, language detected per note) on transcribe.cpp, CPU only, in its own container next to Hermes. The GGUF conversion comes from [handy-computer/parakeet-tdt-0.6b-v3-gguf](https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v3-gguf).

```text
Telegram voice note
  → Hermes STT command provider (small client script in $HERMES_HOME/hooks/)
  → HTTP POST over an internal Docker network
  → stt container: ffmpeg → 16 kHz PCM → Parakeet (model loaded once) → "m:ss text" lines
```

Design points:

- **Model kept loaded.** It loads in under a second and holds about 1.2 GB of RAM. Each note costs only decoding time.
- **No network for the STT container.** The model file is baked into the image at build time, pinned by repository revision and sha256. The container's only network is an `internal: true` bridge shared with the Hermes container, and it publishes no port. It runs read-only, as a non-root user, with no capabilities.
- **Every build input pinned:** base image digest, transcribe.cpp commit, model revision and file hash.
- **Long audio in chunks.** A 2.6-hour file in one pass needed more than 4 GB. The service now cuts audio into pieces of at most 3 minutes, at the quietest 100 ms inside the last 15 seconds of each piece, and offsets the timestamps. Each piece adds about 0.8 GB of scratch memory, so a 3 GB limit holds any length; the 2.6-hour file took 8.4 minutes.
- **Same transcript shape as before.** Lines start with `m:ss` so skills that build outlines or strip timestamps keep working. A new line starts at a sentence end once the line is 4 s long, at a pause over 1.2 s, or after 30 s.
- **Health is checked end to end.** The deploy script and the periodic box check post one second of silence from inside the Hermes container and expect a valid reply. A container health check alone would not show that Hermes can reach it.

The Hermes side is a named command provider. A sketch (paths are illustrative):

```yaml
stt:
  enabled: true
  provider: parakeet_local
  providers:
    parakeet_local:
      type: command
      command: python3 $HERMES_HOME/hooks/stt-client.py {input_path} --output_dir {output_dir} --output_path {output_path} --timestamps
      format: txt
      timeout_seconds: 1200
```

The client only uploads the file and writes the transcript to `{output_path}`. The server is about 200 lines of standard-library Python over transcribe.cpp's ctypes binding.

## 5. Trade-offs to know

- Parakeet sometimes writes numbers as words and English names in Russian speech in Cyrillic (`ГЛМ` for GLM). Whisper kept English terms in Latin script better. A post-transcription glossary cleanup handles known terms.
- An English label inside Russian speech may come out lowercase or half-transliterated (`morning pages`, `morning пейджет`). If a skill routes on a spoken trigger, let it accept such variants.
- Occasionally a whole note comes back with little punctuation.
- Parakeet has no prompt or vocabulary input. That removes a Whisper failure mode (a prompt leaking words into unrelated notes) but also a tuning lever.
- No audio length limit in transcribe.cpp's Parakeet path, but memory grows with length; chunk it.
- Upstream Hermes' built-in `local` provider still uses faster-whisper. It is a reasonable fallback while the sidecar is down; turn its VAD off if quiet openings matter.

## 6. Repeat the test on your own notes

1. Copy a few dozen cached voice notes from the Hermes audio cache to a private directory outside any git repository. Keep the copies private and delete them afterwards.
2. Convert each to 16 kHz mono WAV and compute the loud-minus-quiet frame gap. Keep the noisiest ten and a few clean ones.
3. Transcribe every note with each candidate, timing each call. Run Whisper the way production does; for the rest, transcribe.cpp's CLI takes `-m model.gguf` and a WAV file.
4. Compare word counts per note. A model that is far below the others on a noisy note is dropping speech; one far above may be inventing it. Then listen to the noisiest notes while reading the candidates side by side.
5. Decide on noisy notes, not clean ones: on clean audio the candidates look the same.
6. After choosing, hand-correct about five of the winner's transcripts and keep them as a private test set. Score word error rate against it whenever the model or runtime changes. Correcting from one model's output biases the set toward that model, so use it to catch regressions, not to rank candidates.

Never publish the transcripts. The numbers above are counts and timings only.

## 7. Limits of this evidence

- One speaker, one microphone setup, one host.
- One note was truly noisy; most "noisy" picks were moderate.
- No German notes and one English note in the sample.
- The bake-off itself had no reference transcripts. The 1.2% word error rate comes from five later references corrected from Parakeet's own output.

Re-run the comparison when you change model, quantization or runtime, and when your recording habits change.
