using UnityEngine;
using UnityEngine.EventSystems;

public class MenuSelectorFollower : MonoBehaviour
{
    [SerializeField] RectTransform selectorImage;

    float selectorX; // locked in place, set once at Start

    void Start()
    {
        selectorX = selectorImage.anchoredPosition.x;
    }

    void Update()
    {
        GameObject selected = EventSystem.current.currentSelectedGameObject;
        if (selected == null) return;

        RectTransform selectedRect = selected.GetComponent<RectTransform>();
        if (selectedRect == null) return;

        float targetY = selectedRect.anchoredPosition.y;
        selectorImage.anchoredPosition = new Vector2(selectorX, targetY);
    }
}