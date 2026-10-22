<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_account_admin\Functional;

use Drupal\Tests\farm_test\Functional\FarmBrowserTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests access to user 1.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class UserAccessTest extends FarmBrowserTestBase {

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_account_admin',
  ];

  /**
   * Test user 1 access.
   */
  public function testUser1Access() {

    // Create and login a user with farm_account_admin role.
    $user = $this->createUser();
    $user->addRole('farm_account_admin');
    $user->save();
    $this->drupalLogin($user);

    // Confirm that the user cannot access user 1.
    $this->drupalGet('user/1');
    $this->assertSession()->statusCodeEquals(403);
    $this->drupalGet('user/1/edit');
    $this->assertSession()->statusCodeEquals(403);
  }

}
