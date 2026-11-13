using UnityEngine;


public class ParallaxEffect : MonoBehaviour
{
private float length,startposi;
public GameObject cam;
public float parallaxEffect;
public GameObject player;

  void Start()
    {
        startposi= transform.position.x;
        length = GetComponent<SpriteRenderer>().bounds.size.x;
        
    }

   void LateUpdate()
{
    float temp = (cam.transform.position.x * (1 - parallaxEffect));
    float dist = (player.transform.position.x - startposi) * parallaxEffect;

    transform.position = new Vector3(
        startposi + dist,
        transform.position.y,
        transform.position.z
    );

    if (temp > startposi + length) 
        startposi += length;
    else if (temp < startposi - length) 
        startposi -= length;
}
}
