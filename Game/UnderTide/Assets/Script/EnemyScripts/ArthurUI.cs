using UnityEngine;
using UnityEngine.UI;

public class AurethUI : MonoBehaviour
{
    [SerializeField] private Health aurethHealth;
    [SerializeField] private AurethBoss aurethBoss;
    [SerializeField] private SpriteRenderer aurethSprite;

    [SerializeField] private GameObject uiRoot; // the parent holding health+stamina+name
    [SerializeField] private Image healthFill;
    [SerializeField] private Image staminaFill;

    private void Update()
    {
        bool visible = aurethSprite != null && aurethSprite.isVisible;
        uiRoot.SetActive(visible);

        if (!visible) return;

        if (aurethHealth != null && healthFill != null)
            healthFill.fillAmount = aurethHealth.currentHealth / aurethHealth.MaxHealth;

        if (aurethBoss != null && staminaFill != null)
            staminaFill.fillAmount = aurethBoss.CurrentStamina / aurethBoss.MaxStamina;
    }
}