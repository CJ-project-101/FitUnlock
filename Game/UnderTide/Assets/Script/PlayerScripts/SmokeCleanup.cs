using UnityEngine;

public class SmokeCleanup : MonoBehaviour
{
    public float lifetime = 0.5f;   // match this to SmokePoof.anim's actual length

    private void Start()
    {
        Destroy(gameObject, lifetime);
    }
}