# Example script to read track metadata from a music file.

import mutagen

def extract_mutagen_metadata(file_path):
    print(f"--- Metadata for {file_path} ---")
    
    # mutagen.File automatically detects the file type (mp3, wav, etc.)
    audio = mutagen.File(file_path)
    
    if audio is None:
        print("Could not read file.")
        return

    # 1. Technical Information (Duration, Bitrate, Sample Rate, etc.)
    print("\n[Technical Info]")
    print(f"Duration: {audio.info.length:.2f} seconds")
    print(f"Channels: {audio.info.channels}")
    print(f"Sample Rate: {audio.info.sample_rate} Hz")
    if hasattr(audio.info, 'bitrate'):
        print(f"Bitrate: {audio.info.bitrate} bps")

    # 2. Tag Information (Artist, Title, Album, etc.)
    print("\n[Tags]")
    if audio.tags:
        for key, value in audio.tags.items():
            if key == "APIC:Cover":
                continue
            if key == "WOAS":
                id = str(value).replace("https://suno.com/song/", "")
                print(f"Identifier: {id}")
           # Some values are list-like, others are single frame objects (e.g. WOAS).
            if isinstance(value, (list, tuple)):
                rendered = ", ".join(map(str, value))
            else:
                rendered = str(value)
            print(f"{key}: {rendered}")
    
            '''
            This prints e.g.
            [Tags]
            TIT2: Before the Storm (Short Quiet ACE 522a)
            Identifier: fe9019aa-debb-4c72-859d-589a38b44835
            WOAS: https://suno.com/song/fe9019aa-debb-4c72-859d-589a38b44835
            TPE1: lukewarm_paradise
            COMM::eng: made with suno; created=2026-02-21T20:10:50.403Z; id=fe9019aa-debb-4c72-859d-589a38b44835
            '''

    else:
        print("No tags found.")
    print("\n")

file = "./music/Before the Storm.mp3"
extract_mutagen_metadata(file)
