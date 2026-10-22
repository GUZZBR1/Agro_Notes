<?php

declare(strict_types=1);

namespace Drupal\Tests\farm_ui_dashboard\Functional;

use Drupal\Tests\farm_test\Functional\FarmBrowserTestBase;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests the farmOS dashboard functionality.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class DashboardTest extends FarmBrowserTestBase {

  /**
   * Test user.
   *
   * @var \Drupal\user\UserInterface|bool
   */
  protected $user;

  /**
   * {@inheritdoc}
   */
  protected static $modules = [
    'farm_land',
    'farm_animal',
    'farm_plant',
    'farm_ui_dashboard',
    'farm_ui_dashboard_test',
  ];

  /**
   * {@inheritdoc}
   */
  protected function setUp(): void {
    parent::setUp();

    // Create and login a user with necessary permissions.
    $this->user = $this->createUser(['access farm dashboard']);
    $this->drupalLogin($this->user);
  }

  /**
   * Run all tests.
   */
  public function testAll() {
    $this->doTestGettingStarted();
    $this->doTestDashboardBlock();
    $this->doTestDashboardView();
  }

  /**
   * Test the first-run guide and its form destinations on a clean farm.
   */
  public function doTestGettingStarted() {
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Sua fazenda começa aqui');
    $this->assertSession()->pageTextContains('Cadastre a primeira área');
    $this->assertSession()->pageTextNotContains('Localize a propriedade');
    $this->assertSession()->pageTextContains('0 de 3 etapas concluídas');
    $this->assertSession()->pageTextContains('Nenhuma área cadastrada ainda.');
    $this->assertSession()->pageTextContains('0 áreas, 0 animais e 0 plantas cadastrados');
    $this->assertSession()->pageTextContains('0 atividades registradas');

    $this->assertSession()->elementExists('css', 'a[href="/asset/add/land"]');
    $this->assertSession()->elementExists('css', 'a[href="/asset/add/animal"]');
    $this->assertSession()->elementExists('css', 'a[href="/asset/add/plant"]');
    $this->assertSession()->elementExists('css', 'a[href="/log/add"]');
  }

  /**
   * Test that custom blocks are added to the dashboard.
   */
  public function doTestDashboardBlock() {
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);

    // Assert that the test block was not added to the dashboard.
    $this->assertSession()->pageTextNotContains('Test block title');
    $this->assertSession()->pageTextNotContains('This is the dashboard test block.');

    // Grant permission to view the block.
    $user = $this->createUser(['access farm dashboard', 'access dashboard test block']);
    $this->drupalLogin($user);

    // Assert that the test block was added to the dashboard.
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);
    $this->assertSession()->pageTextContains('Test block title');
    $this->assertSession()->pageTextContains('This is the dashboard test block.');
    $this->assertSession()->pageTextNotContains('Dashboard map placeholder');
  }

  /**
   * Test that custom views are added to the dashboard.
   */
  public function doTestDashboardView() {
    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);

    // Assert that the test view was not added to the dashboard.
    $this->assertSession()->pageTextNotContains('User list');
    $this->assertSession()->pageTextNotContains($this->user->getAccountName());

    $user = $this->createUser(['access farm dashboard', 'access user profiles']);
    $this->drupalLogin($user);

    $this->drupalGet('/dashboard');
    $this->assertSession()->statusCodeEquals(200);

    // Assert that the test view was added to the dashboard.
    $this->assertSession()->pageTextContains('User list');
    $this->assertSession()->pageTextContains($user->getAccountName());
  }

}
