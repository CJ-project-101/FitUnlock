using UnityEngine;
using UnityEngine.InputSystem;

public class WallTestTrigger : MonoBehaviour
{
    [SerializeField] private DestructibleWall testWall;

    void OnTestHeavy(InputValue value)
    {
        if (value.isPressed)
            testWall.OnHeavyAttackHit();
    }

    void OnTestMagic(InputValue value)
    {
        if (value.isPressed)
            testWall.OnMagicHit();
    }
}