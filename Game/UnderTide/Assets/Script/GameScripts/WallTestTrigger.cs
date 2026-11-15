using UnityEngine;
using UnityEngine.InputSystem;

public class WallTestTrigger : MonoBehaviour
{
    [SerializeField] private DestructibleWall testWall;
    [SerializeField] private AurethBoss testBoss;

    void OnTestHeavy(InputValue value)
    {
        if (!value.isPressed) return;
        testWall.OnHeavyAttackHit();
        testBoss.OnHeavyAttackPerformed();
    }

    void OnTestMagic(InputValue value)
    {
        if (!value.isPressed) return;
        testWall.OnMagicHit();
        testBoss.OnMagicCastPerformed();
    }
}