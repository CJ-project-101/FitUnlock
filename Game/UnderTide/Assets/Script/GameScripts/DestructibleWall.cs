using UnityEngine;

public class DestructibleWall : MonoBehaviour
{
    [Header("Boulder Prefab")]
    [SerializeField] private GameObject boulderPrefab;

    [Header("Heavy Attack Hits")]
    [SerializeField] private Transform heavySpawnPoint;
    [Range(0f, 1f)]
    [SerializeField] private float heavyHitDropChance = 0.5f;

    [Header("Magic Hits")]
    [SerializeField] private Transform magicSpawnPoint;
    [SerializeField] private int magicHitsRequired = 4;
    [Range(0f, 1f)]
    [SerializeField] private float magicHitDropChance = 0.5f;
    private int magicHitCount = 0;

    [Header("Cooldown")]
    [SerializeField] private float spawnCooldown = 1f;
    private float cooldownTimer = 0f;

    private void Update()
    {
        if (cooldownTimer > 0f)
            cooldownTimer -= Time.deltaTime;
    }

    public void OnHeavyAttackHit()
    {
        if (cooldownTimer > 0f) return;

        if (Random.value <= heavyHitDropChance)
            SpawnBoulder(heavySpawnPoint);

        cooldownTimer = spawnCooldown;
    }

    public void OnMagicHit()
    {
        magicHitCount++;

        if (magicHitCount >= magicHitsRequired)
        {
            magicHitCount = 0;

            if (Random.value <= magicHitDropChance)
                SpawnBoulder(magicSpawnPoint);
        }
    }

    private void SpawnBoulder(Transform spawnPoint)
    {
        if (boulderPrefab == null || spawnPoint == null) return;
        Instantiate(boulderPrefab, spawnPoint.position, Quaternion.identity);
    }
}