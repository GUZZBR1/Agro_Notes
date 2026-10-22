<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_sensor_listener\Functional;

use Drupal\Tests\farm_sensor\Functional\SensorDataApiTest;
use Drupal\asset\Entity\AssetInterface;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Test the sensor listener (legacy) API.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class SensorListenerApiTest extends SensorDataApiTest {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_sensor_listener',
  ];

  /**
   * Helper function to build the path to the sensor API.
   *
   * @param \Drupal\asset\Entity\AssetInterface $asset
   *   The asset.
   *
   * @return string
   *   The path.
   */
  protected function buildPath(AssetInterface $asset) {
    $public_key = $asset->get('public_key')->value;
    return "base://farm/sensor/listener/{$public_key}";
  }

}
