using UnityEngine;
using UnityEngine.Audio;

public class SoundManager : MonoBehaviour
{
    public static SoundManager instance;

    [Header("SFX")]
    [SerializeField] AudioSource sfxSource;

    [Header("Music")]
    [SerializeField] AudioSource musicSource;
    [SerializeField] AudioClip[] musicTracks;
    [SerializeField] bool shuffleMusic = false;

    [Header("Mixer")]
    [SerializeField] AudioMixer audioMixer;

    int currentTrackIndex = -1;
    bool musicEnabled = true;

    const string SfxVolumeKey = "SFXVolume";
    const string MusicVolumeKey = "MusicVolume";

    void Awake()
    {
        if (instance != null && instance != this)
        {
            Destroy(gameObject);
            return;
        }
        instance = this;
        DontDestroyOnLoad(gameObject);

        musicSource.loop = false;
        musicEnabled = PlayerPrefs.GetInt("MusicEnabled", 1) == 1;

        // Apply saved mixer volumes
        SetSFXVolume(PlayerPrefs.GetFloat(SfxVolumeKey, 0.75f));
        SetMusicVolume(PlayerPrefs.GetFloat(MusicVolumeKey, 0.75f));
    }

    void Start()
    {
        if (musicTracks != null && musicTracks.Length > 0 && musicEnabled)
            PlayNextTrack();
    }

    void Update()
    {
        if (musicEnabled && musicSource != null && musicTracks != null && musicTracks.Length > 0)
        {
            if (!musicSource.isPlaying && currentTrackIndex != -1)
                PlayNextTrack();
        }
    }

    public void PlaySound(AudioClip clip)
    {
        if (clip == null || sfxSource == null) return;
        sfxSource.PlayOneShot(clip);
    }

    void PlayNextTrack()
    {
        if (musicTracks.Length == 0) return;
        currentTrackIndex = shuffleMusic
            ? Random.Range(0, musicTracks.Length)
            : (currentTrackIndex + 1) % musicTracks.Length;

        musicSource.clip = musicTracks[currentTrackIndex];
        musicSource.Play();
    }

    public void SetMusicEnabled(bool enabled)
    {
        musicEnabled = enabled;
        PlayerPrefs.SetInt("MusicEnabled", enabled ? 1 : 0);

        if (!enabled) musicSource.Stop();
        else if (!musicSource.isPlaying) PlayNextTrack();
    }

    // Volume is stored 0-1 (slider-friendly), converted to decibels for the mixer.
    public void SetSFXVolume(float linearVolume)
    {
        float dB = linearVolume > 0.0001f ? Mathf.Log10(linearVolume) * 20f : -80f;
        audioMixer.SetFloat("SFXVolume", dB);
        PlayerPrefs.SetFloat(SfxVolumeKey, linearVolume);
    }

    public void SetMusicVolume(float linearVolume)
    {
        float dB = linearVolume > 0.0001f ? Mathf.Log10(linearVolume) * 20f : -80f;
        audioMixer.SetFloat("MusicVolume", dB);
        PlayerPrefs.SetFloat(MusicVolumeKey, linearVolume);
    }

    public float GetSavedSFXVolume() => PlayerPrefs.GetFloat(SfxVolumeKey, 0.75f);
    public float GetSavedMusicVolume() => PlayerPrefs.GetFloat(MusicVolumeKey, 0.75f);
}