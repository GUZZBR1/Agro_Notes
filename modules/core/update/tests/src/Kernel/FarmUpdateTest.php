<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_update\Kernel;

use Drupal\KernelTests\KernelTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for farmOS Update module.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class FarmUpdateTest extends KernelTestBase {

  /**
   * The config factory service.
   *
   * @var \Drupal\Core\Config\ConfigFactoryInterface
   */
  protected $configFactory;

  /**
   * The farm update service.
   *
   * @var \Drupal\farm_update\FarmUpdateInterface
   */
  protected $farmUpdate;

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'config_update',
    'farm_update',
    'farm_update_test',
    'farm_field',
    'farm_flag',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();
    $this->configFactory = \Drupal::service('config.factory');
    $this->farmUpdate = \Drupal::service('farm.update');
    $this->installEntitySchema('flag');
    $this->installConfig([
      'farm_update_test',
      'farm_flag',
    ]);
  }

  /**
   * Test farmOS Update module.
   */
  public function testFarmUpdate() {

    // Confirm that unmanaged overridden config does not get reverted.
    $this->farmUpdateTestRevertSetting('farm_flag.flag.monitor', 'label', 'Changed', FALSE);

    // Confirm that managed config listed in hook_farm_update_managed_config()
    // does get reverted.
    $this->farmUpdateTestRevertSetting('farm_flag.flag.priority', 'label', 'Changed');

    // Confirm that managed config listed in farm_update.settings does get
    // reverted.
    $this->farmUpdateTestRevertSetting('farm_flag.flag.review', 'label', 'Changed');

    // Confirm that managed config listed in hook_farm_update_managed_config()
    // can be removed with hook_farm_update_managed_config_alter(), and does
    // not get reverted.
    $this->farmUpdateTestRevertSetting('farm_flag.flag.test', 'label', 'Changed', FALSE);
  }

  /**
   * Helper method to test reverting a setting.
   *
   * @param string $config
   *   Configuration name.
   * @param string $setting
   *   Setting name within the configuration.
   * @param string $override
   *   Value to use for override.
   * @param bool $reverted
   *   Whether we expect this config to be reverted. Defaults to TRUE. If set to
   *   FALSE, then we expect that the config will still be overridden after
   *   rebuild.
   */
  protected function farmUpdateTestRevertSetting(string $config, string $setting, string $override, bool $reverted = TRUE) {
    $original = \Drupal::config($config)->get($setting);
    $this->configFactory->getEditable($config)->set($setting, $override)->save();
    $this->assertEquals($override, \Drupal::config($config)->get($setting), 'Setting is overridden before rebuild.');
    $this->farmUpdate->rebuild();
    $expected_value = $reverted ? $original : $override;
    $expected_message = $reverted ? 'Setting is reverted after rebuild.' : 'Setting is overridden after rebuild.';
    $this->assertEquals($expected_value, \Drupal::config($config)->get($setting), $expected_message);
  }

}
