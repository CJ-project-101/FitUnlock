using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using TMPro;
using UnityEngine.EventSystems;

public class MainMenuManager : MonoBehaviour
{
    [Header("Main Buttons")]
    [SerializeField] Button continueButton;
    [SerializeField] Button newGameButton;

    [Header("Settings Panel")]
    [SerializeField] GameObject settingsPanel;
    [SerializeField] Button openSettingsButton;
    [SerializeField] Button closeSettingsButton;

    [Header("Audio Controls")]
    [SerializeField] Slider musicVolumeSlider;
    [SerializeField] Slider sfxVolumeSlider;
    [SerializeField] Button musicToggleButton;
    [SerializeField] TMP_Text musicToggleLabel;
    [SerializeField] Button Quit;

[Header("Main Menu Group")]
[SerializeField] GameObject buttonsPanel;   // the "Buttons" parent in Hierarchy
[SerializeField] GameObject selector; 

    [Header("Scene Settings")]
    [SerializeField] string gameplaySceneName = "Level1";

    const string SaveExistsKey = "HasSave";
    const string VolumeKey = "Volume";
    const string MusicEnabledKey = "MusicEnabled";

    bool musicEnabled;

    void Start()
    {
        SetupContinueButton();
        SetupVolumeSlider();
        SetupMusicToggle();
        SetupSettingsPanel();

        newGameButton.onClick.AddListener(StartNewGame);
        Quit.onClick.AddListener(QuitGame);

        GameObject firstSelected = continueButton.interactable ? continueButton.gameObject : newGameButton.gameObject;
        EventSystem.current.SetSelectedGameObject(continueButton.gameObject);
    }

    void SetupContinueButton()
    {
        bool hasSave = PlayerPrefs.GetInt(SaveExistsKey, 0) == 1;
        continueButton.interactable = hasSave;
        continueButton.onClick.AddListener(ContinueGame);
    }

    void SetupVolumeSlider()
    {
        if (SoundManager.instance == null) return;

        musicVolumeSlider.value = SoundManager.instance.GetSavedMusicVolume();
        sfxVolumeSlider.value = SoundManager.instance.GetSavedSFXVolume();

        musicVolumeSlider.onValueChanged.AddListener(SoundManager.instance.SetMusicVolume);
        sfxVolumeSlider.onValueChanged.AddListener(SoundManager.instance.SetSFXVolume);
    }

    void SetupMusicToggle()
    {
        musicEnabled = PlayerPrefs.GetInt(MusicEnabledKey, 1) == 1;
        UpdateMusicToggleLabel();

        musicToggleButton.onClick.AddListener(ToggleMusic);
    }

    void SetupSettingsPanel()
{
    settingsPanel.SetActive(false);

    openSettingsButton.onClick.AddListener(() =>
    {
        settingsPanel.SetActive(true);
        buttonsPanel.SetActive(false);
        selector.SetActive(false);
    });

    closeSettingsButton.onClick.AddListener(() =>
    {
        settingsPanel.SetActive(false);
        buttonsPanel.SetActive(true);
        selector.SetActive(true);
    });
}

    void OnVolumeChanged(float value)
    {
        ApplyVolume(value);
        PlayerPrefs.SetFloat(VolumeKey, value);
    }

    void ApplyVolume(float value)
    {
        // Global volume — swap for an AudioMixer parameter once you add a music system.
        AudioListener.volume = value;
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
        {
            musicToggleLabel.text = musicEnabled ? "Music: On" : "Music: Off";
        }
    }

    void ContinueGame()
    {
        SceneManager.LoadScene(gameplaySceneName);
    }

    void StartNewGame()
    {
        PlayerPrefs.SetInt(SaveExistsKey, 1);
        // TODO: reset actual save data here once your save system exists.
        SceneManager.LoadScene(gameplaySceneName);
    }

    void QuitGame()
    {
        Application.Quit();
    }
}