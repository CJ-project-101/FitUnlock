using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;

public class ScreenFader : MonoBehaviour
{
    public Image panel;               
    public float fadeDuration = 0.6f;

    void Reset()
    {
        panel = GetComponentInChildren<Image>();
    }

    // Fade out then call callback
    public void FadeOut(Action onComplete = null)
    {
        StopAllCoroutines();
        StartCoroutine(Fade(panel.color.a, 1f, fadeDuration, onComplete));
    }

    // Fade in
    public void FadeIn(Action onComplete = null)
    {
        StopAllCoroutines();
        StartCoroutine(Fade(panel.color.a, 0f, fadeDuration, onComplete));
    }

    IEnumerator Fade(float fromAlpha, float toAlpha, float duration, Action onComplete)
    {
        float t = 0f;
        Color c = panel.color;

        while (t < duration)
        {
            t += Time.deltaTime;
            float a = Mathf.Lerp(fromAlpha, toAlpha, t / duration);
            c.a = a;
            panel.color = c;
            yield return null;
        }

        c.a = toAlpha;
        panel.color = c;

        onComplete?.Invoke();
    }
}