<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_setup\Functional;

use Drupal\Tests\farm_test\Functional\FarmBrowserTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests for the farmOS setup wizard.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class SetupWizardTest extends FarmBrowserTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_setup',
    'farm_ui_dashboard',
  ];

  /**
   * Tests the farmOS setup wizard functionality.
   */
  public function testSetupWizard() {

    /** @var \Drupal\farm_setup\SetupWizardInterface $wizard */
    $wizard = \Drupal::service('farm_setup.wizard');

    // Initialize the setup wizard state so that the welcome form is displayed
    // on the dashboard.
    $wizard->setBlockPluginId('welcome');

    // Login a user with access to the dashboard.
    $permissions = ['access farm dashboard'];
    $user = $this->createUser($permissions);
    $this->drupalLogin($user);

    // Go to the dashboard and confirm that the setup block is not visible.
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextNotContains('Setup progress');
    $this->assertSession()->pageTextNotContains('Step 1: Welcome');
    $this->assertSession()->pageTextNotContains('Welcome to farmOS');

    // Login a user with additional access to the setup wizard.
    $permissions[] = 'access farm setup wizard';
    $user = $this->createUser($permissions);
    $this->drupalLogin($user);

    // Go to the dashboard and confirm that the setup block is visible.
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Setup progress');
    $this->assertSession()->pageTextContains('Step 1: Welcome');
    $this->assertSession()->pageTextContains('0%');
    $this->assertSession()->pageTextContains('Welcome to farmOS');
    $this->assertSession()->responseContains('value="Continue"');
    $this->assertSession()->responseNotContains('value="Save and continue"');
    $this->assertSession()->responseNotContains('value="Skip"');

    // Press the "Continue" button and confirm that the resources form is shown
    // (because the user does not have permission to install modules).
    $this->getSession()->getPage()->pressButton('Continue');
    $this->assertSession()->pageTextContains('Setup progress');
    $this->assertSession()->pageTextContains('Step 2: Resources');
    $this->assertSession()->pageTextContains('100%');
    $this->assertSession()->pageTextContains('Next steps');

    // Since this is now the last step, confirm there is only a "Finish" button.
    $this->assertSession()->responseContains('value="Finish"');
    $this->assertSession()->responseNotContains('value="Continue"');
    $this->assertSession()->responseNotContains('value="Save and continue"');
    $this->assertSession()->responseNotContains('value="Skip"');

    // Refresh the page and confirm that the resources form is still shown.
    // This tests that the progress is saved to Drupal state.
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Step 2: Resources');

    // Login a user with additional access to install modules.
    $permissions[] = 'install farm modules';
    $user = $this->createUser($permissions);
    $this->drupalLogin($user);

    // Refresh the page and confirm that the modules form is now shown, and that
    // both "Save and continue" and "Skip" buttons are visible, but "Continue"
    // and "Finish" are not.
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Step 2: Install modules');
    $this->assertSession()->pageTextContains('50%');
    $this->assertSession()->pageTextContains('What are your record keeping needs?');
    $this->assertSession()->responseContains('value="Save and continue"');
    $this->assertSession()->responseContains('value="Skip"');
    $this->assertSession()->responseNotContains('value="Continue"');
    $this->assertSession()->responseNotContains('value="Finish"');

    // Skip submission of the modules form. This will be tested separately.
    $this->getSession()->getPage()->pressButton('Skip');

    // Confirm that we are on the resources step again.
    $this->assertSession()->pageTextContains('Step 3: Resources');
    $this->assertSession()->pageTextContains('100%');

    // Install the farm_setup_test module, reset the current plugin to modules,
    // reload the page, press the "Skip" button, and confirm that we see the
    // test form.
    $wizard->setBlockPluginId('modules');
    \Drupal::service('module_installer')->install(['farm_setup_test']);
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Step 2: Install modules');
    $this->assertSession()->pageTextContains('33%');
    $this->getSession()->getPage()->pressButton('Skip');
    $this->assertSession()->pageTextContains('Step 3: Test');
    $this->assertSession()->pageTextContains('67%');
    $this->assertSession()->pageTextContains('This is just a test');
    $this->assertSession()->pageTextContains('Pay no attention.');

    // Test form validation.
    $this->getSession()->getPage()->fillField('test', 'validate');
    $this->getSession()->getPage()->pressButton('Save and continue');
    $this->assertSession()->pageTextContains('Step 3: Test');
    $this->assertSession()->pageTextContains('Validation test passed.');

    // Test skipping the test form.
    $this->getSession()->getPage()->pressButton('Skip');
    $this->assertSession()->pageTextNotContains('Validation test passed.');
    $this->assertSession()->pageTextContains('Step 4: Resources');

    // Reset the state, reload the page, and confirm that we see the test form.
    $wizard->setBlockPluginId('test');
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Step 3: Test');

    // Test form submission.
    $this->getSession()->getPage()->pressButton('Save and continue');
    $this->assertSession()->pageTextContains('Submission test passed.');

    // Confirm that we are on the resources step again, then press the "Finish"
    // button and confirm that the block is no longer visible, and a message is
    // displayed to the user.
    $this->assertSession()->pageTextContains('Step 4: Resources');
    $this->assertSession()->pageTextContains('100%');
    $this->getSession()->getPage()->pressButton('Finish');
    $this->assertSession()->pageTextNotContains('Setup progress');
    $this->assertSession()->pageTextContains('farmOS setup is complete! Happy record keeping!');

    // Confirm that we can also go through the setup process via /setup/wizard,
    // and that it redirects back to the dashboard with a message at the end.
    $this->drupalGet('/setup/wizard');
    $this->assertSession()->statusCodeEquals(200);
    $this->getSession()->getPage()->pressButton('Continue');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->addressEquals('setup/wizard/modules');
    $this->getSession()->getPage()->pressButton('Skip');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->addressEquals('setup/wizard/test');
    $this->getSession()->getPage()->pressButton('Skip');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->addressEquals('setup/wizard/resources');
    $this->getSession()->getPage()->pressButton('Finish');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->addressEquals('');
    $this->assertSession()->pageTextContains('farmOS setup is complete! Happy record keeping!');

    // Remove the user's "install farm modules" permission and confirm that
    // /setup/wizard/modules is no longer accessible.
    $user = $this->createUser(array_filter($permissions, function ($perm) {
      return $perm != 'install farm modules';
    }));
    $this->drupalLogin($user);
    $this->drupalGet('/setup/wizard/modules');
    $this->assertSession()->statusCodeEquals(403);
  }

}
