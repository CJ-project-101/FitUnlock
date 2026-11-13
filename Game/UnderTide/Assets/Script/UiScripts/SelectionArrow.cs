using UnityEngine;
using UnityEngine.UI;

public class SelectionArrow : MonoBehaviour
{
    [SerializeField] private RectTransform[] buttons;
    [SerializeField] private AudioClip changeSound;
    [SerializeField] private AudioClip interactSound;
    [SerializeField] private float yOffset = -8f;

    private RectTransform arrow;
    private int currentPosition;

    private void Awake()
    {
        arrow = GetComponent<RectTransform>();
    }

private void OnEnable()
{
    currentPosition = 0;
    StartCoroutine(SnapNextFrame());
}

private System.Collections.IEnumerator SnapNextFrame()
{
    yield return null; // wait one frame
    AssignPosition();
}

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.UpArrow) || Input.GetKeyDown(KeyCode.W))
            ChangePosition(-1);
        if (Input.GetKeyDown(KeyCode.DownArrow) || Input.GetKeyDown(KeyCode.S))
            ChangePosition(1);

        if (Input.GetKeyDown(KeyCode.KeypadEnter) || Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.E))
            Interact();
    }

    private void ChangePosition(int _change)
    {
        Debug.Log("ChangePosition called, change=" + _change);
        currentPosition += _change;

        if (_change != 0 && SoundManager.instance != null)
            SoundManager.instance.PlaySound(changeSound);

        if (currentPosition < 0)
            currentPosition = buttons.Length - 1;
        else if (currentPosition > buttons.Length - 1)
            currentPosition = 0;

        AssignPosition();
    }

    // Called by ButtonHoverNotifier when the mouse hovers a button
    public void SetPosition(int index)
    {
        if (index == currentPosition) return;

        currentPosition = index;

        if (SoundManager.instance != null)
            SoundManager.instance.PlaySound(changeSound);

        AssignPosition();
    }

    private void AssignPosition()
    {
        Vector3 pos = arrow.position;
        pos.y = buttons[currentPosition].position.y + yOffset;
        arrow.position = pos;
    }

    private void Interact()
    {
        if (SoundManager.instance != null)
            SoundManager.instance.PlaySound(interactSound);

        buttons[currentPosition].GetComponent<Button>().onClick.Invoke();
    }
}