<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_setup\FunctionalJavascript;

use Drupal\Tests\farm_test\FunctionalJavascript\FarmWebDriverTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests installing modules via the setup wizard modules form.
 *
 * @see \Drupal\farm_setup\Plugin\SetupForm\SetupModulesForm
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class SetupModulesFormTest extends FarmWebDriverTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_setup',
    'farm_setup_test_modules',
    'farm_ui_dashboard',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    // Set the initial setup wizard block plugin state to show the modules form.
    \Drupal::service('farm_setup.wizard')->setBlockPluginId('modules');

    // Login a user with access to the dashboard, setup wizard, and module
    // installation setup form.
    $user = $this->createUser([
      'access farm dashboard',
      'access farm setup wizard',
      'install farm modules',
    ]);
    $this->drupalLogin($user);
  }

  /**
   * Tests the setup wizard modules form.
   */
  public function testModulesSetupForm() {

    // Request the dashboard.
    $this->drupalGet('<front>');

    // Confirm that checkboxes are unchecked, and modules are not installed.
    $this->assertCheckboxState('plant', FALSE, FALSE);
    $this->assertCheckboxState('land', FALSE, FALSE);
    $this->assertCheckboxState('activity', FALSE, FALSE);
    $this->assertModuleInstalled('farm_plant', FALSE);
    $this->assertModuleInstalled('farm_land', FALSE);
    $this->assertModuleInstalled('farm_land_types', FALSE);
    $this->assertModuleInstalled('farm_activity', FALSE);

    // Check the plant checkbox and confirm that a summary message is displayed.
    $this->getSession()->getPage()->checkField('plant');
    $this->assertTrue($this->assertSession()->waitForText('The following modules will be installed: Plant asset'));

    // Confirm that the recommended modules warning is displayed.
    $recommended_title = 'Recommendations';
    $recommended_message = 'It is recommended that at least one location asset type and one basic log type is installed. To proceed anyway, use the "Ignore recommendations" checkbox below.';
    $this->assertSession()->pageTextContains($recommended_title);
    $this->assertSession()->pageTextContains($recommended_message);

    // Confirm that the ignore_recommended checkbox is visible and required.
    $ignore_recommended = $this->getSession()->getPage()->findField('ignore_recommended');
    $this->assertNotEmpty($ignore_recommended);
    $this->assertTrue($ignore_recommended->hasClass('required'));
    $this->assertFalse($ignore_recommended->isChecked());

    // Check the ignore_recommended checkbox and submit the form.
    $ignore_recommended->check();
    $this->getSession()->getPage()->pressButton('Save and continue');

    // Wait for the batch process to complete.
    $this->assertTrue($this->assertSession()->waitForText('Step 3: Resources', 30000));

    // Rebuild the container.
    $this->rebuildContainer();

    // Reset state so that we can see the modules form and reload the dashboard.
    \Drupal::service('farm_setup.wizard')->setBlockPluginId('modules');
    $this->drupalGet('<front>');

    // Confirm that the modules form is visible, the plant checkbox is checked,
    // and the farm_plant module is installed.
    $this->assertSession()->pageTextContains('Step 2: Install modules');
    $this->assertCheckboxState('plant', TRUE, TRUE);
    $this->assertModuleInstalled('farm_plant', TRUE);

    // Confirm that the recommended modules warning and ignore_recommended
    // checkbox is still visible and required.
    $this->assertSession()->pageTextContains($recommended_title);
    $this->assertSession()->pageTextContains($recommended_message);
    $ignore_recommended = $this->getSession()->getPage()->findField('ignore_recommended');
    $this->assertNotEmpty($ignore_recommended);
    $this->assertTrue($ignore_recommended->hasClass('required'));
    $this->assertFalse($ignore_recommended->isChecked());

    // Check the land and activity checkboxes and confirm that the summary
    // message is updated.
    $this->getSession()->getPage()->checkField('land');
    $this->assertTrue($this->assertSession()->waitForText('The following modules will be installed: Land asset, Default land types'));
    $this->getSession()->getPage()->checkField('activity');
    $this->assertTrue($this->assertSession()->waitForText('Activity log, Land asset, Default land types, Standard quantity'));

    // Confirm that the recommended modules warning and ignore_recommended
    // checkbox is not visible.
    $this->assertSession()->pageTextNotContains($recommended_title);
    $this->assertSession()->pageTextNotContains($recommended_message);
    $this->assertEmpty($this->getSession()->getPage()->findField('ignore_recommended'));

    // Submit the form, wait for the batch process to complete, and rebuild the
    // container.
    $this->getSession()->getPage()->pressButton('Save and continue');
    $this->assertTrue($this->assertSession()->waitForText('Step 3: Resources', 30000));
    $this->rebuildContainer();

    // Reset state so that we can see the modules form and reload the dashboard.
    \Drupal::service('farm_setup.wizard')->setBlockPluginId('modules');
    $this->drupalGet('<front>');

    // Confirm that the modules form is visible, the plant, land, and activity
    // checkboxes are checked, and the farm_activity, farm_land,
    // farm_land_types, farm_plant, and farm_quantity_standard modules are
    // installed.
    $this->assertSession()->pageTextContains('Step 2: Install modules');
    $this->assertCheckboxState('plant', TRUE, TRUE);
    $this->assertCheckboxState('land', TRUE, TRUE);
    $this->assertCheckboxState('activity', TRUE, TRUE);
    $this->assertModuleInstalled('farm_activity', TRUE);
    $this->assertModuleInstalled('farm_land', TRUE);
    $this->assertModuleInstalled('farm_land_types', TRUE);
    $this->assertModuleInstalled('farm_plant', TRUE);
    $this->assertModuleInstalled('farm_quantity_standard', TRUE);

    // Confirm that the recommended modules warning and ignore_recommended
    // checkbox is not visible.
    $this->assertSession()->pageTextNotContains($recommended_title);
    $this->assertSession()->pageTextNotContains($recommended_message);
    $this->assertEmpty($this->getSession()->getPage()->findField('ignore_recommended'));

    // Test installing a module that provides a setup form, and confirm that it
    // appears after the modules form.
    $this->assertSession()->pageTextContains('Install farm_setup_test module');
    $this->getSession()->getPage()->checkField('install_farm_setup_test');
    $this->getSession()->getPage()->pressButton('Save and continue');
    $this->assertTrue($this->assertSession()->waitForText('Step 3: Test', 30000));
    $this->assertSession()->pageTextContains('This is just a test');
    $this->assertSession()->pageTextContains('Pay no attention.');
  }

  /**
   * Helper function to assert the state of checkboxes.
   *
   * @param string $field_name
   *   The checkbox input field name.
   * @param bool $checked
   *   Boolean if the checkbox should be checked. Defaults to FALSE.
   * @param bool $disabled
   *   Boolean if the checkbox should be disabled. Defaults to FALSE.
   */
  protected function assertCheckboxState(string $field_name, bool $checked = FALSE, bool $disabled = FALSE) {
    $checkbox = $this->getSession()->getPage()->findField($field_name);
    $this->assertNotEmpty($checkbox);
    $this->assertEquals($checked, $checkbox->isChecked());
    $this->assertEquals($disabled, $checkbox->hasAttribute('disabled'));
  }

  /**
   * Helper function to assert the state of a module.
   *
   * @param string $module
   *   The module name.
   * @param bool $installed
   *   Boolean if the module should be installed. Defaults to TRUE.
   */
  protected function assertModuleInstalled(string $module, bool $installed = TRUE) {
    $this->assertEquals($installed, \Drupal::moduleHandler()->moduleExists($module));
  }

}
