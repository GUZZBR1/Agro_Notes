<?php

declare(strict_types=1);

namespace Drupal\Tests\plan\Functional;

use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\plan\Entity\Plan;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\RunTestsInSeparateProcesses;

/**
 * Tests the plan CRUD.
 */
#[Group('farm')]
#[RunTestsInSeparateProcesses]
class PlanCRUDTest extends PlanTestBase {

  use StringTranslationTrait;

  /**
   * Run all tests.
   */
  public function testAll() {
    $this->doTestFieldsVisibility();
    $this->doTestCreatePlan();
    $this->doTestViewPlan();
    $this->doTestEditPlan();
    $this->doTestDeletePlan();
  }

  /**
   * Fields are displayed correctly.
   */
  public function doTestFieldsVisibility() {
    $this->drupalGet('plan/add/default');
    $assert_session = $this->assertSession();
    $assert_session->statusCodeEquals(200);
    $assert_session->fieldExists('name[0][value]');
    $assert_session->fieldExists('status');
    $assert_session->fieldExists('revision_log_message[0][value]');
    $assert_session->fieldExists('uid[0][target_id]');
    $assert_session->fieldExists('created[0][value][date]');
    $assert_session->fieldExists('created[0][value][time]');
  }

  /**
   * Create plan entity.
   */
  public function doTestCreatePlan() {
    $assert_session = $this->assertSession();
    $name = $this->randomMachineName();
    $edit = [
      'name[0][value]' => $name,
    ];

    $this->drupalGet('plan/add/default');
    $this->submitForm($edit, 'Save');

    $result = \Drupal::entityTypeManager()
      ->getStorage('plan')
      ->getQuery()
      ->accessCheck(TRUE)
      ->range(0, 1)
      ->execute();
    $plan_id = reset($result);
    $plan = Plan::load($plan_id);
    $this->assertEquals($plan->get('name')->value, $name, 'plan has been saved.');

    $assert_session->pageTextContains("Saved plan: $name");
    $assert_session->pageTextContains($name);
  }

  /**
   * Display plan entity.
   */
  public function doTestViewPlan() {
    $edit = [
      'name' => $this->randomMachineName(),
      'created' => \Drupal::time()->getRequestTime(),
    ];
    $plan = $this->createPlanEntity($edit);
    $plan->save();

    $this->drupalGet($plan->toUrl('canonical'));
    $this->assertSession()->statusCodeEquals(200);

    $this->assertSession()->pageTextContains($edit['name']);
    $this->assertSession()->responseContains(\Drupal::service('date.formatter')->format(\Drupal::time()->getRequestTime()));
  }

  /**
   * Edit plan entity.
   */
  public function doTestEditPlan() {
    $plan = $this->createPlanEntity();
    $plan->save();

    $edit = [
      'name[0][value]' => $this->randomMachineName(),
    ];
    $this->drupalGet($plan->toUrl('edit-form'));
    $this->submitForm($edit, 'Save');

    $this->assertSession()->pageTextContains($edit['name[0][value]']);
  }

  /**
   * Delete plan entity.
   */
  public function doTestDeletePlan() {
    $plan = $this->createPlanEntity();
    $plan->save();

    $label = $plan->getName();
    $plan_id = $plan->id();

    $this->drupalGet($plan->toUrl('delete-form'));
    $this->submitForm([], 'Delete');
    $this->assertSession()->responseContains($this->t('The @entity-type %label has been deleted.', [
      '@entity-type' => $plan->getEntityType()->getSingularLabel(),
      '%label' => $label,
    ]));
    $this->assertNull(Plan::load($plan_id));
  }

}
