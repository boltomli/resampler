from io import BytesIO
from pathlib import Path

from gooey import Gooey, GooeyParser
from loguru import logger
from pedalboard import Limiter, LowpassFilter, Mix, Pedalboard
from pedalboard.io import AudioFile


def transcode(
    audio_bytes: bytes, sample_rate: int = 48000, filter: bool = True
) -> bytes:
    result = BytesIO()
    try:
        with AudioFile(BytesIO(audio_bytes), "r") as audio_file:
            boards_mix = []
            audio_samplerate = int(audio_file.samplerate)
            if not sample_rate:
                sample_rate = audio_samplerate
            if sample_rate <= audio_samplerate:
                audio_data = audio_file.read(audio_file.frames)
                if filter and (sample_rate < audio_samplerate):
                    board = Pedalboard([LowpassFilter(sample_rate / 2)])
                    intermediate_data = board(audio_data, audio_file.samplerate)
                    intermediate_file = BytesIO()
                    with AudioFile(
                        intermediate_file, "w", audio_samplerate, format="wav"
                    ) as o:
                        o.write(intermediate_data)
                    intermediate_file.seek(0)
                    with AudioFile(intermediate_file, "r").resampled_to(
                        sample_rate
                    ) as i:
                        audio_data = i.read(i.frames)
            else:
                with AudioFile(BytesIO(audio_bytes), "r").resampled_to(
                    sample_rate
                ) as resampled_file:
                    audio_data = resampled_file.read(resampled_file.frames)
                if filter:
                    boards_mix.append(LowpassFilter(audio_samplerate / 2))
            if boards_mix:
                boards = [Mix(boards_mix), Limiter(0)]
                board = Pedalboard(boards)
                audio_data = board(audio_data, sample_rate)
        with AudioFile(result, "w", sample_rate, 1, format="wav", quality=None) as f:
            f.write(audio_data)
    except Exception as e:
        logger.warning(repr(e))
        raise e
    return result.getvalue()


@Gooey
def main():
    parser = GooeyParser()
    parser.add_argument("SourcePath", widget="DirChooser")
    parser.add_argument("TargetPath", widget="DirChooser")
    parser.add_argument(
        "SamplingRate",
        widget="Dropdown",
        choices=["48000", "24000", "16000", "8000"],
        default="48000",
    )
    parser.add_argument("--filter", default=True, action="store_true")
    args = parser.parse_args()

    for wav_file in Path(args.SourcePath).glob("*.wav"):
        src = open(str(wav_file), "rb").read()
        tgt = transcode(src, int(args.SamplingRate), args.filter)
        with open(str(Path(args.TargetPath) / wav_file.name), "wb") as f:
            f.write(tgt)


if __name__ == "__main__":
    main()
