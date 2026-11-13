using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using TMPro;

public class PauseMenuManager : MonoBehaviour
{
    [Header("Buttons")]
    [SerializeField] Button resumeButton;
    [SerializeField] Button settingsButton;
    [SerializeField] Button mainMenuButton;
    [SerializeField] Button quitButton;

    [Header("Settings Panel")]
    [SerializeField] GameObject settingsPanel;
    [SerializeField] Button closeSettingsButton;

    [Header("Audio Controls")]
    [SerializeField] Slider musicVolumeSlider;
    [SerializeField] Slider sfxVolumeSlider;
    [SerializeField] Button musicToggleButton;
    [SerializeField] TMP_Text musicToggleLabel;

    [Header("Main Menu Group")]
    [SerializeField] GameObject buttonsPanel;
    [SerializeField] GameObject selector;

    [SerializeField] string mainMenuSceneName = "MainMenu";

    const string VolumeKey = "Volume";
    const string MusicEnabledKey = "MusicEnabled";
    bool musicEnabled;

    void Start()
    {
        resumeButton.onClick.AddListener(Resume);
        settingsButton.onClick.AddListener(OpenSettings);
        closeSettingsButton.onClick.AddListener(CloseSettings);
        mainMenuButton.onClick.AddListener(GoToMainMenu);
        quitButton.onClick.AddListener(QuitGame);

        settingsPanel.SetActive(false);

        SetupVolumeSlider();
        SetupMusicToggle();
    }

    void SetupVolumeSlider()
    {
        if (SoundManager.instance == null) return;

        musicVolumeSlider.value = SoundManager.instance.GetSavedMusicVolume();
        sfxVolumeSlider.value = SoundManager.instance.GetSavedSFXVolume();

        musicVolumeSlider.onValueChanged.AddListener(SoundManager.instance.SetMusicVolume);
        sfxVolumeSlider.onValueChanged.AddListener(SoundManager.instance.SetSFXVolume);
    }

    void OnVolumeChanged(float value)
    {
        AudioListener.volume = value;
        PlayerPrefs.SetFloat(VolumeKey, value);
    }

    void SetupMusicToggle()
    {
        musicEnabled = PlayerPrefs.GetInt(MusicEnabledKey, 1) == 1;
        UpdateMusicToggleLabel();
        musicToggleButton.onClick.AddListener(ToggleMusic);
    }

    void ToggleMusic()
    {
        musicEnabled = !musicEnabled;
        UpdateMusicToggleLabel();

        if (SoundManager.instance != null)
            SoundManager.instance.SetMusicEnabled(musicEnabled);
    }

    void UpdateMusicToggleLabel()
    {
        if (musicToggleLabel != null)
            musicToggleLabel.text = musicEnabled ? "Music: On" : "Music: Off";
    }

    void Resume() => SessionManager.Instance?.CloseExitMenu();

    void OpenSettings()
    {
        settingsPanel.SetActive(true);
        buttonsPanel.SetActive(false);
        selector.SetActive(false);
    }

    void CloseSettings()
    {
        settingsPanel.SetActive(false);
        buttonsPanel.SetActive(true);
        selector.SetActive(true);
    }

    void GoToMainMenu()
    {
        Time.timeScale = 1f;
        SceneManager.LoadScene(mainMenuSceneName);
    }

    void QuitGame() => SessionManager.Instance?.ExitGame();
}