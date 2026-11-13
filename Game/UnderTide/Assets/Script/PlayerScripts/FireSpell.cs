using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

public class FireSpell : MonoBehaviour
{
    [Header("Spell Prefabs")]
    [SerializeField] private GameObject fireSpellPrefab;
    [SerializeField] private GameObject fireSpellUpPrefab;

    [Header("Spawn Points")]
    [SerializeField] private Transform firePoint;
    [SerializeField] private Transform firePointUp;

    private static readonly List<RaycastResult> uiHits = new List<RaycastResult>();

    public void OnFire(InputValue value)
    {
        if (!value.isPressed || !CanFire()) return;
        FireHorizontal();
    }

    public void OnFireUp(InputValue value)
    {
        if (!value.isPressed || !CanFire()) return;
        FireUp();
    }

    private bool CanFire()
    {
        // Locked or paused: no spells.
        if (Time.timeScale == 0f) return false;

        // Exit menu open: no spells.
        SessionManager sm = SessionManager.Instance;
        if (sm != null && sm.IsExitMenuOpen) return false;

        // Click landed on a UI button (e.g. the three-dot menu): no spell.
        if (IsMouseClickingUIButton()) return false;

        return true;
    }

    private bool IsMouseClickingUIButton()
    {
        if (EventSystem.current == null || Mouse.current == null) return false;

        // Only a real mouse press counts, so gamepad firing is never blocked
        // just because the cursor is resting over a button.
        if (!Mouse.current.leftButton.isPressed && !Mouse.current.rightButton.isPressed)
            return false;

        var data = new PointerEventData(EventSystem.current)
        {
            position = Mouse.current.position.ReadValue()
        };

        uiHits.Clear();
        EventSystem.current.RaycastAll(data, uiHits);

        foreach (RaycastResult hit in uiHits)
        {
            if (hit.module is GraphicRaycaster &&
                hit.gameObject.GetComponentInParent<Selectable>() != null)
                return true;
        }
        return false;
    }

    private void FireHorizontal()
    {
        if (fireSpellPrefab == null || firePoint == null)
        {
            Debug.LogWarning("FireSpell: Horizontal prefab or FirePoint is missing!");
            return;
        }

        float direction = Mathf.Sign(transform.root.localScale.x);

        GameObject spell = Instantiate(fireSpellPrefab, firePoint.position, Quaternion.identity);

        Bullet bullet = spell.GetComponent<Bullet>();
        if (bullet != null)
        {
            bullet.SetDirection(new Vector2(direction, 0f));
            bullet.SetPlayerFirePosition(transform.root.position);
        }
    }

    private void FireUp()
    {
        if (fireSpellUpPrefab == null || firePointUp == null)
        {
            Debug.LogWarning("FireSpell: Up prefab or FirePointUp is missing!");
            return;
        }

        GameObject spell = Instantiate(fireSpellUpPrefab, firePointUp.position,
                                       Quaternion.Euler(0f, 0f, -90f));

        Bullet bullet = spell.GetComponent<Bullet>();
        if (bullet != null)
        {
            bullet.SetDirection(Vector2.up);
            bullet.SetPlayerFirePosition(transform.root.position);
        }
    }
}