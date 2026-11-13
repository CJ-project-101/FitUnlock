using UnityEngine;
using UnityEngine.EventSystems;

public class ButtonHoverNotifier : MonoBehaviour, IPointerEnterHandler
{
    [SerializeField] private SelectionArrow selectionArrow;
    [SerializeField] private int buttonIndex;

    public void OnPointerEnter(PointerEventData eventData)
    {
        selectionArrow.SetPosition(buttonIndex);
    }
}